from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


class InvalidState(ValueError):
    pass


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class StateSigner:
    def __init__(self, secret: str) -> None:
        if len(secret) < 24:
            raise ValueError("GITHUB_STATE_SECRET must be at least 24 characters")
        self._secret = secret.encode("utf-8")

    def sign(self, *, purpose: str, claims: dict[str, Any], ttl_seconds: int = 600) -> str:
        payload = {
            **claims,
            "purpose": purpose,
            "exp": int(time.time()) + ttl_seconds,
            "nonce": secrets.token_urlsafe(18),
        }
        encoded = _b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = _b64encode(
            hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest()
        )
        return f"{encoded}.{signature}"

    def verify(self, value: str, *, purpose: str) -> dict[str, Any]:
        try:
            encoded, provided_signature = value.split(".", 1)
            expected_signature = _b64encode(
                hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(provided_signature, expected_signature):
                raise InvalidState("State signature is invalid")
            payload = json.loads(_b64decode(encoded))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            if isinstance(exc, InvalidState):
                raise
            raise InvalidState("State value is malformed") from exc

        if payload.get("purpose") != purpose:
            raise InvalidState("State purpose is invalid")
        if not isinstance(payload.get("exp"), int) or payload["exp"] < int(time.time()):
            raise InvalidState("State has expired")
        return payload


def new_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = _b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def verify_webhook_signature(*, secret: str, body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
