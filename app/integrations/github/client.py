from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.core.settings import Settings
from app.schemas.github import GitHubRepository


class GitHubAPIError(RuntimeError):
    pass


class GitHubClient:
    api_base = "https://api.github.com"
    api_version = "2022-11-28"

    def __init__(self, config: Settings) -> None:
        self.config = config

    def oauth_authorize_url(self, *, state: str, code_challenge: str) -> str:
        params = urlencode(
            {
                "client_id": self.config.github_client_id,
                "redirect_uri": self.config.github_oauth_callback_url,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"https://github.com/login/oauth/authorize?{params}"

    async def exchange_code(self, *, code: str, code_verifier: str) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.config.github_client_id,
                    "client_secret": self.config.github_client_secret,
                    "code": code,
                    "redirect_uri": self.config.github_oauth_callback_url,
                    "code_verifier": code_verifier,
                },
            )
        payload = self._json(response, "GitHub OAuth exchange failed")
        token = payload.get("access_token")
        if not token:
            raise GitHubAPIError(
                str(payload.get("error_description") or "GitHub did not return a user token")
            )
        return str(token)

    async def verify_installation_for_user(
        self, *, user_token: str, installation_id: int
    ) -> dict[str, Any]:
        for page in range(1, 101):
            payload = await self._api_get(
                f"/user/installations?per_page=100&page={page}", token=user_token
            )
            installations = payload.get("installations", [])
            installation = next(
                (
                    item
                    for item in installations
                    if int(item.get("id", -1)) == installation_id
                ),
                None,
            )
            if installation is not None:
                return installation
            if len(installations) < 100:
                break
        raise GitHubAPIError("The signed-in GitHub user cannot access this installation")

    async def list_user_installation_repositories(
        self, *, user_token: str, installation_id: int
    ) -> list[GitHubRepository]:
        repositories: list[GitHubRepository] = []
        for page in range(1, 101):
            payload = await self._api_get(
                f"/user/installations/{installation_id}/repositories?per_page=100&page={page}",
                token=user_token,
            )
            items = payload.get("repositories", [])
            repositories.extend(
                GitHubRepository(
                    id=int(item["id"]),
                    full_name=str(item["full_name"]),
                    private=bool(item.get("private", False)),
                    default_branch=str(item.get("default_branch") or "main"),
                )
                for item in items
            )
            if len(items) < 100:
                break
        return repositories

    async def verify_repository_access(
        self, *, installation_id: int, repository: GitHubRepository
    ) -> None:
        token = await self._installation_token(
            installation_id=installation_id,
            repository_id=repository.id,
        )
        await self._api_get(f"/repos/{repository.full_name}", token=token)

    async def _installation_token(self, *, installation_id: int, repository_id: int) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.api_base}/app/installations/{installation_id}/access_tokens",
                headers=self._headers(self._app_jwt()),
                json={
                    "repository_ids": [repository_id],
                    "permissions": {"contents": "read"},
                },
            )
        payload = self._json(response, "Could not create a GitHub installation token")
        token = payload.get("token")
        if not token:
            raise GitHubAPIError("GitHub did not return an installation token")
        return str(token)

    def _app_jwt(self) -> str:
        now = int(time.time())
        return jwt.encode(
            {"iat": now - 60, "exp": now + 540, "iss": self.config.github_app_id},
            self.config.read_github_private_key(),
            algorithm="RS256",
        )

    async def _api_get(self, path: str, *, token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.api_base}{path}", headers=self._headers(token))
        return self._json(response, f"GitHub request failed for {path}")

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": self.api_version,
            "User-Agent": "OpenFDE-GitHub-Connector",
        }

    @staticmethod
    def _json(response: httpx.Response, fallback: str) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubAPIError(fallback) from exc
        if response.is_error:
            message = payload.get("message") if isinstance(payload, dict) else None
            raise GitHubAPIError(str(message or fallback))
        if not isinstance(payload, dict):
            raise GitHubAPIError(fallback)
        return payload
