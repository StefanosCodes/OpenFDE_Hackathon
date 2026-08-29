import pytest
from fastapi import HTTPException

from app.services.url_fetch import _is_blocked_ip, _validate_public_https_url


@pytest.mark.asyncio
async def test_rejects_non_https_url():
    with pytest.raises(HTTPException) as exc:
        await _validate_public_https_url("http://example.com")

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_rejects_loopback_url(monkeypatch):
    async def fake_to_thread(fn, *args):
        return [(None, None, None, None, ("127.0.0.1", 443))]

    monkeypatch.setattr("app.services.url_fetch.asyncio.to_thread", fake_to_thread)

    with pytest.raises(HTTPException) as exc:
        await _validate_public_https_url("https://localhost")

    assert exc.value.status_code == 422


def test_blocks_private_and_metadata_ips():
    import ipaddress

    assert _is_blocked_ip(ipaddress.ip_address("10.0.0.1"))
    assert _is_blocked_ip(ipaddress.ip_address("169.254.169.254"))
