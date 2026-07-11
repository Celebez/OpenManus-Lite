"""Lightweight web-fetch tool (zero external dependencies).

Replaces the heavy Playwright/Chromium browser for environments where
installing a real browser is impractical (Termux, minimal containers).

It fetches a URL with the stdlib only and returns either cleaned visible
text or the raw HTML — no JavaScript execution, no browser binary.
"""

from __future__ import annotations

import asyncio
import gzip
import html
import http.client
import json
import urllib.parse
import urllib.request
from email.parser import BytesHeaderParser
from html.parser import HTMLParser
from typing import Optional

from app.tool.base import BaseTool, ToolResult


class _TextExtractor(HTMLParser):
    """Strip tags and keep roughly visible text + <title>/<a> hints."""

    VOID = {"script", "style", "head", "meta", "link", "noscript", "template"}
    BLOCK = {"p", "div", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6",
             "section", "article", "ul", "ol", "table", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            self._skip += 1
        if tag in self.BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.VOID and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            text = data.strip()
            if text:
                self._parts.append(text)

    def text(self) -> str:
        return "\n".join(p for p in self._parts if p.strip() or p == "\n")


def _fetch(url: str, timeout: int) -> tuple[int, dict, bytes]:
    headers = {
        "User-Agent": "OpenManus-Lite/1.0 (+https://github.com/Celebez/OpenManus-Lite)",
        "Accept-Encoding": "gzip",
        "Accept": "text/html,application/json,application/xhtml+xml,*/*;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        raw = resp.headers
        status = resp.status
        # gather lower-cased headers into a plain dict
        hdrs = {k.lower(): v for k, v in raw.items()}
        # urllib may auto-decompress; if not, do it ourselves
        if hdrs.get("content-encoding") == "gzip" and body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        return status, hdrs, body


class WebFetch(BaseTool):
    name: str = "web_fetch"
    description: str = (
        "Fetch a web page or API and return its content. "
        "Lightweight (no browser): returns cleaned text for HTML, or parsed JSON "
        "for application/json. Use instead of the heavy browser tool."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to fetch."},
            "timeout": {"type": "integer", "description": "Seconds before giving up.", "default": 20},
            "raw": {"type": "boolean", "description": "Return raw HTML instead of cleaned text.", "default": False},
        },
        "required": ["url"],
    }

    async def execute(self, url: str, timeout: int = 20, raw: bool = False) -> ToolResult:
        try:
            status, hdrs, body = await asyncio.to_thread(_fetch, url, int(timeout))
        except urllib.error.HTTPError as e:
            return self.fail_response(f"HTTP {e.code}: {e.reason}")
        except http.client.HTTPException as e:
            return self.fail_response(f"HTTP error: {e}")
        except Exception as e:  # network / timeout / SSL
            return self.fail_response(f"Fetch failed: {type(e).__name__}: {e}")

        ctype = (hdrs.get("content-type") or "text/html").lower()

        if "application/json" in ctype:
            try:
                data = json.loads(body.decode("utf-8", "replace"))
                return self.success_response(json.dumps(data, indent=2)[:16000])
            except Exception:
                pass  # fall through to text

        if raw:
            return self.success_response(body.decode("utf-8", "replace")[:16000])

        # Cleaned text path
        try:
            text = body.decode("utf-8", "replace")
        except Exception:
            text = body.decode("latin-1", "replace")
        parser = _TextExtractor()
        parser.feed(text)
        cleaned = html.unescape(parser.text()).strip()
        if not cleaned:
            cleaned = text[:8000]
        return self.success_response(cleaned[:16000])
