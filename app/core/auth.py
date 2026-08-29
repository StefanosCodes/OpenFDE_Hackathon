from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from app.core.database import get_pool


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str
    name: str


SEEDED_TOKENS = {
    "user-a": UUID("11111111-1111-1111-1111-111111111111"),
    "user-b": UUID("22222222-2222-2222-2222-222222222222"),
}


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    token = _extract_bearer_token(authorization)
    user_id = SEEDED_TOKENS.get(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
        )

    row = await get_pool().fetchrow(
        """
        SELECT id, email, name
        FROM users
        WHERE id = $1
        """,
        user_id,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Seeded user does not exist",
        )
    return CurrentUser(id=row["id"], email=row["email"], name=row["name"])


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


CurrentUserDep = Depends(get_current_user)
