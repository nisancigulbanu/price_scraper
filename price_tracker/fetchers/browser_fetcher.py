from __future__ import annotations

from .static_fetcher import FetchError, FetchResponse


def fetch_with_browser(url: str) -> FetchResponse:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - optional runtime dependency
        raise FetchError("Playwright is not installed or browsers are not available") from exc

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(locale="tr-TR")
            page.goto(url, wait_until="networkidle", timeout=30_000)
            html = page.content()
            final_url = page.url
            browser.close()
            return FetchResponse(html=html, status_code=200, final_url=final_url)
    except Exception as exc:  # pragma: no cover - depends on browser runtime
        raise FetchError(f"Playwright fetch failed: {exc}") from exc
