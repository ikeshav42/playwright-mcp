"""Standalone MCP server: fetch JavaScript-rendered webpages as clean Markdown."""

from collections.abc import AsyncIterator
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from urllib.parse import urlparse

import trafilatura
from markdownify import markdownify as to_markdown
from mcp.server.fastmcp import Context, FastMCP
from playwright.async_api import Browser, async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
NAV_TIMEOUT_MS = 15_000
SELECTOR_TIMEOUT_MS = 5_000
HYDRATION_WAIT_MS = 1_000
STRIP_TAGS = ["script", "style", "noscript", "svg", "button"]


@dataclass
class AppContext:
    browser: Browser


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Launch one warm Chromium instance shared by all tool calls."""
    # Chromium's own sandbox stays on by default. Inside the Docker image
    # (non-root, no capabilities) it cannot start, so the container acts as the
    # sandbox instead. Playwright disables the sandbox unless told otherwise,
    # so it must be requested explicitly.
    use_sandbox = not os.environ.get("BROWSER_MCP_NO_SANDBOX")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            chromium_sandbox=use_sandbox,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        try:
            yield AppContext(browser=browser)
        finally:
            await browser.close()


mcp = FastMCP("browser-mcp", lifespan=lifespan)


@mcp.tool(
    name="fetch_webpage_markdown",
    description=(
        "Navigates to a webpage using a headless browser to execute client-side "
        "JavaScript, extracts core content while stripping navigation and ads, "
        "and converts it to token-efficient Markdown."
    ),
)
async def fetch_webpage_markdown(
    url: str, ctx: Context, wait_for_selector: str = ""
) -> str:
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError("Only http:// and https:// URLs are allowed.")
    browser = ctx.request_context.lifespan_context.browser
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 768},
    )
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)

        if wait_for_selector:
            await page.wait_for_selector(wait_for_selector, timeout=SELECTOR_TIMEOUT_MS)
        else:
            await page.wait_for_timeout(HYDRATION_WAIT_MS)

        raw_html = await page.content()
    finally:
        await context.close()

    extracted = trafilatura.extract(
        raw_html,
        output_format="html",
        include_links=True,
        include_tables=True,
        favor_recall=True,
    )
    clean_html = extracted or raw_html
    return to_markdown(clean_html, heading_style="ATX", strip=STRIP_TAGS).strip()


if __name__ == "__main__":
    mcp.run()
