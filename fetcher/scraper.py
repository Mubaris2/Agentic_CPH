from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

logger = logging.getLogger(__name__)


def _candidate_urls(contest_id: int, index: str) -> list[str]:
    normalized_index = str(index).upper()
    urls = [
        f"https://codeforces.com/contest/{contest_id}/problem/{normalized_index}",
        f"https://codeforces.com/problemset/problem/{contest_id}/{normalized_index}",
        f"https://codeforces.com/contest/{contest_id}/problem/{normalized_index}?locale=en",
        f"https://codeforces.com/problemset/problem/{contest_id}/{normalized_index}?locale=en",
    ]
    seen = set()
    out = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


class _BrowserManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def get_page(self) -> Page:
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            if self._browser is None:
                self._browser = await self._playwright.chromium.launch(headless=True)
            if self._context is None:
                self._context = await self._browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                )
            return await self._context.new_page()


_browser_manager = _BrowserManager()


async def fetch_problem_html(contest_id: int, index: str, retries: int = 3) -> str:
    target_urls = _candidate_urls(contest_id, index)
    errors = []

    for target_url in target_urls:
        for attempt in range(1, retries + 1):
            page = None
            try:
                page = await _browser_manager.get_page()
                await page.goto("https://codeforces.com/", wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(1200)
                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(1500)

                html = await page.content()
                lower_html = html.lower()
                if any(token in lower_html for token in ["captcha", "verify you are human", "cloudflare", "access denied"]):
                    msg = f"attempt {attempt}: anti-bot challenge page at {target_url}"
                    logger.warning(msg)
                    errors.append(msg)
                else:
                    try:
                        await page.wait_for_selector(".problem-statement", timeout=20000)
                        await page.wait_for_timeout(800)
                        html = await page.content()
                    except PlaywrightTimeoutError:
                        pass

                    if ".problem-statement" in html:
                        return html

                    msg = f"attempt {attempt}: statement selector not found at {target_url}"
                    logger.warning(msg)
                    errors.append(msg)
            except PlaywrightTimeoutError as exc:
                msg = f"attempt {attempt}: timeout while fetching {target_url}: {exc}"
                logger.warning(msg)
                errors.append(msg)
            except Exception as exc:
                msg = f"attempt {attempt}: scrape error for {target_url}: {exc}"
                logger.warning(msg)
                errors.append(msg)
            finally:
                if page is not None:
                    await page.close()

            await asyncio.sleep(2 ** (attempt - 1))

    raise RuntimeError("Codeforces scrape failed after retries: " + " | ".join(errors))
