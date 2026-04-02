"""HTTP fetch tool with HTML to Markdown conversion."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

try:
    import html2text
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    html2text = None

from .base import BaseTool, ToolResult

_MAX_OUTPUT = 50 * 1024


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch a web page and convert HTML to Markdown."
    input_schema = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }

    async def run(self, input: dict) -> ToolResult:
        url = str(input.get("url", ""))
        if self._is_private_url(url):
            return ToolResult(content=[{"type": "text", "text": "Blocked private/internal URL"}], is_error=True)
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url)
        except httpx.RequestError as exc:
            return ToolResult(content=[{"type": "text", "text": f"Fetch failed: {exc}"}], is_error=True)
        text = response.text
        if "html" in response.headers.get("content-type", ""):
            text = html2text.html2text(text) if html2text is not None else _strip_html(text)
        clipped = text.encode()[:_MAX_OUTPUT].decode(errors="replace")
        return ToolResult(content=[{"type": "text", "text": clipped}])

    def _is_private_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return True
        try:
            addr = ipaddress.ip_address(parsed.hostname)
            return addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            try:
                infos = socket.getaddrinfo(parsed.hostname, None)
            except socket.gaierror:
                return False
            for info in infos:
                ip = ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return True
            return False


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text)
