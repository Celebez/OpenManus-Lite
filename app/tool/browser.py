"""Browser automation tool backed by Playwright.

Supports a small, self-contained action set: ``navigate``, ``click``,
``type``, ``extract`` (read text/content), and ``screenshot``. A single
browser/context/page is lazily created and reused across calls, then cleaned
up via ``cleanup()``.
"""
from __future__ import annotations

import base64
from typing import Optional

from app.tool.base import BaseTool, ToolResult


class Browser(BaseTool):
    name: str = "browser"
    description: str = (
        "Automate a real web browser (Playwright/Chromium). "
        "Actions: navigate (go to URL), click (CSS selector), type (fill a field), "
        "extract (return visible text), screenshot (return base64 PNG)."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "click", "type", "extract", "screenshot"],
            },
            "url": {"type": "string", "description": "URL for navigate."},
            "selector": {
                "type": "string",
                "description": "CSS selector for click / type / extract.",
            },
            "text": {"type": "string", "description": "Text to type."},
        },
        "required": ["action"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._playwright = None
        self._browser = None
        self._page = None

    async def _ensure_page(self):
        if self._page is not None:
            return self._page
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        ctx = await self._browser.new_context()
        self._page = await ctx.new_page()
        return self._page

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
    ) -> ToolResult:
        try:
            page = await self._ensure_page()
            if action == "navigate":
                if not url:
                    return self.fail_response("navigate requires 'url'")
                await page.goto(url, wait_until="load", timeout=30000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                return self.success_response(f"Navigated to {url}")
            if action == "click":
                if not selector:
                    return self.fail_response("click requires 'selector'")
                await page.click(selector, timeout=10000)
                return self.success_response(f"Clicked '{selector}'")
            if action == "type":
                if not selector or text is None:
                    return self.fail_response("type requires 'selector' and 'text'")
                await page.fill(selector, text, timeout=10000)
                return self.success_response(f"Typed into '{selector}'")
            if action == "extract":
                if selector:
                    data = await page.locator(selector).inner_text()
                else:
                    data = await page.inner_text("body")
                return self.success_response(data[:8000])
            if action == "screenshot":
                png = await page.screenshot()
                b64 = base64.b64encode(png).decode()
                result = ToolResult(output="Screenshot captured (base64 PNG)")
                result.base64_image = b64
                return result
            return self.fail_response(f"Unknown action: {action}")
        except Exception as e:
            return self.fail_response(f"Browser error: {e}")

    async def cleanup(self):
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        finally:
            self._browser = None
            self._page = None
            self._playwright = None
