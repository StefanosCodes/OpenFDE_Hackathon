from __future__ import annotations

import asyncio
import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from app.core.http import unprocessable


MAX_URL_BYTES = 2 * 1024 * 1024
URL_TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 5
ACCEPTED_URL_CONTENT_TYPES = {
    "text/html",
    "text/plain",
    "text/markdown",
    "application/pdf",
}


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._hidden_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and not self._hidden_depth:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)


async def fetch_url_source(url: str) -> tuple[bytes, str, str | None]:
    current_url = url
    async with httpx.AsyncClient(timeout=URL_TIMEOUT_SECONDS, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await _validate_public_https_url(current_url)
            async with client.stream("GET", current_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise unprocessable("URL redirect is missing a location")
                    current_url = str(response.url.join(location))
                    continue

                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise unprocessable("URL returned an unsuccessful status") from exc
                content_type = _base_content_type(response.headers.get("content-type"))
                if content_type not in ACCEPTED_URL_CONTENT_TYPES:
                    raise unprocessable("Unsupported URL content type")
                data = await _read_capped_response(response)
                if content_type == "text/html":
                    parser = _VisibleTextParser()
                    parser.feed(data.decode(response.encoding or "utf-8", errors="replace"))
                    text = parser.text().encode("utf-8")
                    return text, "text/plain", current_url
                return data, content_type, current_url
    raise unprocessable("Too many URL redirects")


async def _read_capped_response(response: httpx.Response) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > MAX_URL_BYTES:
            raise unprocessable("URL response is too large")
        chunks.append(chunk)
    return b"".join(chunks)


def _base_content_type(value: str | None) -> str:
    if not value:
        return "application/octet-stream"
    return value.split(";", 1)[0].strip().lower()


async def _validate_public_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise unprocessable("Only https URLs are allowed")
    if not parsed.hostname:
        raise unprocessable("URL must include a hostname")
    infos = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, parsed.port or 443)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _is_blocked_ip(ip):
            raise unprocessable("URL host resolves to a blocked address")


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )
