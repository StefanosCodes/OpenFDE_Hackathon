from __future__ import annotations

import json
from typing import Literal
from urllib.parse import quote, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.core.auth import CurrentUser, get_current_user
from app.core.settings import Settings, get_settings
from app.integrations.github.client import GitHubClient
from app.integrations.github.repository import (
    GitHubConnectionRecord,
    GitHubConnectionRepository,
    get_github_connection_repository,
)
from app.integrations.github.security import (
    InvalidState,
    StateSigner,
    new_pkce_pair,
    verify_webhook_signature,
)
from app.schemas.github import (
    GitHubConnectResponse,
    GitHubConnectionResponse,
    GitHubRepository,
    GitHubRepositorySelection,
)


router = APIRouter(tags=["github connector"])


def get_github_client(config: Settings = Depends(get_settings)) -> GitHubClient:
    return GitHubClient(config)


def _configured(config: Settings) -> None:
    missing = config.missing_github_settings()
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "GitHub connection is not configured", "missing": missing},
        )


def _signer(config: Settings) -> StateSigner:
    if not config.github_state_secret:
        _configured(config)
        raise AssertionError("unreachable")
    try:
        return StateSigner(config.github_state_secret)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": str(exc), "missing": ["GITHUB_STATE_SECRET"]},
        ) from exc


def _response(record: GitHubConnectionRecord | None) -> GitHubConnectionResponse:
    if record is None:
        return GitHubConnectionResponse.disconnected()
    return GitHubConnectionResponse(
        status=record.status,
        account_login=record.account_login,
        repository=record.repository,
        last_error=record.last_error,
        updated_at=record.updated_at,
    )


@router.post("/connectors/github/connect", response_model=GitHubConnectResponse)
async def connect_github(
    return_mode: Literal["page", "popup"] = Query(default="page"),
    user: CurrentUser = Depends(get_current_user),
    config: Settings = Depends(get_settings),
    repository: GitHubConnectionRepository = Depends(get_github_connection_repository),
) -> GitHubConnectResponse:
    _configured(config)
    state_value = _signer(config).sign(
        purpose="github_install",
        claims={"user_id": str(user.id), "return_mode": return_mode},
    )
    await repository.begin(user.id)
    connect_url = (
        f"https://github.com/apps/{config.github_app_slug}/installations/new"
        f"?state={quote(state_value)}"
    )
    return GitHubConnectResponse(status="connecting", connect_url=connect_url)


@router.get("/integrations/github/setup", include_in_schema=False)
async def github_setup(
    installation_id: int = Query(gt=0),
    state: str = Query(min_length=10),
    config: Settings = Depends(get_settings),
    github: GitHubClient = Depends(get_github_client),
) -> RedirectResponse:
    _configured(config)
    try:
        install_claims = _signer(config).verify(state, purpose="github_install")
    except InvalidState as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    verifier, challenge = new_pkce_pair()
    oauth_state = _signer(config).sign(
        purpose="github_oauth",
        claims={
            "user_id": install_claims["user_id"],
            "installation_id": installation_id,
            "return_mode": install_claims.get("return_mode", "page"),
        },
    )
    response = RedirectResponse(
        github.oauth_authorize_url(state=oauth_state, code_challenge=challenge),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        "openfde_github_pkce",
        verifier,
        max_age=600,
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        path="/v1/integrations/github/oauth/callback",
    )
    return response


@router.get("/integrations/github/oauth/callback", include_in_schema=False)
async def github_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    config: Settings = Depends(get_settings),
    github: GitHubClient = Depends(get_github_client),
    repository: GitHubConnectionRepository = Depends(get_github_connection_repository),
) -> RedirectResponse:
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_description or error,
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth code or state",
        )
    try:
        claims = _signer(config).verify(state, purpose="github_oauth")
    except InvalidState as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    verifier = request.cookies.get("openfde_github_pkce")
    if not verifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing PKCE verifier")

    owner_user_id = UUID(str(claims["user_id"]))
    installation_id = int(claims["installation_id"])
    user_token = await github.exchange_code(code=code, code_verifier=verifier)
    installation = await github.verify_installation_for_user(
        user_token=user_token,
        installation_id=installation_id,
    )
    repositories = await github.list_user_installation_repositories(
        user_token=user_token,
        installation_id=installation_id,
    )
    account = installation.get("account") or {}
    await repository.save_installation(
        owner_user_id=owner_user_id,
        installation_id=installation_id,
        account_login=str(account.get("login") or "unknown"),
        account_type=str(account.get("type") or "unknown"),
        repositories=repositories,
    )

    query_values = {"github": "installed"}
    if claims.get("return_mode") == "popup":
        query_values["popup"] = "1"
    query = urlencode(query_values)
    response = RedirectResponse(
        f"{config.frontend_base_url}/connectors?{query}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(
        "openfde_github_pkce",
        path="/v1/integrations/github/oauth/callback",
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/connectors/github", response_model=GitHubConnectionResponse)
async def github_status(
    user: CurrentUser = Depends(get_current_user),
    repository: GitHubConnectionRepository = Depends(get_github_connection_repository),
) -> GitHubConnectionResponse:
    return _response(await repository.get(user.id))


@router.get("/connectors/github/repositories", response_model=list[GitHubRepository])
async def list_github_repositories(
    user: CurrentUser = Depends(get_current_user),
    repository: GitHubConnectionRepository = Depends(get_github_connection_repository),
) -> list[GitHubRepository]:
    connection = await repository.get(user.id)
    if connection is None or connection.status not in {"awaiting_repository", "connected"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub is not ready")
    return await repository.list_repositories(user.id)


@router.put("/connectors/github/repository", response_model=GitHubConnectionResponse)
async def select_github_repository(
    body: GitHubRepositorySelection,
    user: CurrentUser = Depends(get_current_user),
    github: GitHubClient = Depends(get_github_client),
    repository: GitHubConnectionRepository = Depends(get_github_connection_repository),
) -> GitHubConnectionResponse:
    connection = await repository.get(user.id)
    if connection is None or connection.installation_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub is not connected")
    available = await repository.list_repositories(user.id)
    selected = next((item for item in available if item.id == body.repository_id), None)
    if selected is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository is not available")
    await github.verify_repository_access(
        installation_id=connection.installation_id,
        repository=selected,
    )
    try:
        connected = await repository.select_repository(
            owner_user_id=user.id,
            repository_id=body.repository_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _response(connected)


@router.delete("/connectors/github", response_model=GitHubConnectionResponse)
async def disconnect_github(
    user: CurrentUser = Depends(get_current_user),
    repository: GitHubConnectionRepository = Depends(get_github_connection_repository),
) -> GitHubConnectionResponse:
    # This unlinks GitHub from OpenFDE. It intentionally does not uninstall the
    # GitHub App, so organization owners remain in control of installations.
    await repository.disconnect(user.id)
    return GitHubConnectionResponse.disconnected()


@router.post("/integrations/github/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    config: Settings = Depends(get_settings),
    repository: GitHubConnectionRepository = Depends(get_github_connection_repository),
) -> dict[str, bool]:
    if not config.github_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook is not configured",
        )
    body = await request.body()
    if not verify_webhook_signature(
        secret=config.github_webhook_secret,
        body=body,
        signature_header=x_hub_signature_256,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    installation_id = int((payload.get("installation") or {}).get("id", 0))
    action = str(payload.get("action") or "")
    if x_github_event == "installation" and action in {"deleted", "suspend"} and installation_id:
        await repository.disconnect_installation(installation_id, reason=f"installation_{action}")
    if x_github_event == "installation_repositories" and action == "removed" and installation_id:
        removed = {int(item["id"]) for item in payload.get("repositories_removed", [])}
        await repository.remove_repositories(installation_id, removed)
    return {"accepted": True}
