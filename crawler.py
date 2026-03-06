"""crawler.py — Crawl Xianyu (闲鱼) search results and write CrawlRecords to SQLite.

Data flow:
    Xianyu search page (Playwright) → parse item/seller/price → CrawlRecord → SQLite

CLI usage:
    python3 crawler.py --keyword "AI 副业" --dry-run
    python3 crawler.py  # crawl all KEYWORDS for today

The crawler is intentionally resilient: a single keyword failure writes a
zero-record (preserving date continuity) and never aborts the full run.
"""

import argparse
import asyncio
import logging
import random
import sqlite3
from typing import Union

from playwright.async_api import Browser, Page, async_playwright

from config import (
    CrawlRecord,
    KEYWORDS,
    get_db,
    init_db,
    utc_today_str,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(module)s — %(message)s",
    level=logging.INFO,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XIANYU_SEARCH_URL = "https://www.goofish.com/search?q={keyword}&sortValue=GmtModifiedDesc"

# Delay range between keyword requests (seconds) — basic anti-bot courtesy
_DELAY_MIN: float = 2.0
_DELAY_MAX: float = 5.0

# How many pages to scan per keyword (1 page ≈ 25 items)
_PAGES_PER_KEYWORD: int = 2

# User-agent pool — rotated per keyword
_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

# ---------------------------------------------------------------------------
# Page parsing helpers
# ---------------------------------------------------------------------------


def _parse_price(price_str: str) -> float:
    """Extract a numeric price from a raw string like '¥29.9' or '29.90'.

    Returns 0.0 if parsing fails.

    Args:
        price_str: Raw text from the DOM.

    Returns:
        Float price value, or 0.0 on parse error.
    """
    cleaned = price_str.strip().lstrip("¥￥").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


async def _parse_page(page: Page) -> tuple[list[float], list[str]]:
    """Parse one search results page for prices and seller IDs.

    Xianyu renders item cards inside elements with data-item-id attributes.
    Price text lives in elements with class containing 'price'.
    Seller nick lives in elements with class containing 'nick' or 'seller'.

    This selector logic targets the current goofish.com layout and may need
    updating if Xianyu changes their DOM structure.

    Args:
        page: Playwright Page already loaded with search results.

    Returns:
        Tuple of (prices list, seller_ids list).
    """
    prices: list[float] = []
    seller_ids: list[str] = []

    # Wait for item cards to appear (timeout 10s)
    try:
        await page.wait_for_selector("[data-item-id]", timeout=10_000)
    except Exception:
        logger.warning("Timed out waiting for item cards — page may be empty or blocked.")
        return prices, seller_ids

    # Extract price text from all item cards
    price_elements = await page.query_selector_all("[data-item-id] [class*='price']")
    for el in price_elements:
        text = await el.inner_text()
        price = _parse_price(text)
        if price > 0:
            prices.append(price)

    # Extract seller nicknames for unique-seller count
    seller_elements = await page.query_selector_all(
        "[data-item-id] [class*='nick'], [data-item-id] [class*='seller']"
    )
    for el in seller_elements:
        nick = (await el.inner_text()).strip()
        if nick:
            seller_ids.append(nick)

    # Fallback: count any item cards found to estimate item_count
    if not prices:
        item_cards = await page.query_selector_all("[data-item-id]")
        logger.warning("No prices extracted; found %d item cards on this page.", len(item_cards))

    return prices, seller_ids


# ---------------------------------------------------------------------------
# Core fetch function
# ---------------------------------------------------------------------------


async def _fetch_keyword_async(keyword: str, browser: Browser) -> CrawlRecord:
    """Crawl Xianyu for a single keyword across _PAGES_PER_KEYWORD pages.

    Opens a new browser context per keyword (fresh cookies/session) with a
    rotated user-agent. Collects all prices and seller nicknames, then
    aggregates to item_count, seller_count, avg_price.

    Args:
        keyword: Search term, e.g. "AI 副业".
        browser: Playwright Browser instance (shared across keywords).

    Returns:
        CrawlRecord for today's date. On any error, returns a zero-record.
    """
    today = utc_today_str()
    ua = random.choice(_USER_AGENTS)

    context = await browser.new_context(
        user_agent=ua,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    page = await context.new_page()

    all_prices: list[float] = []
    all_sellers: list[str] = []

    try:
        for page_num in range(1, _PAGES_PER_KEYWORD + 1):
            url = XIANYU_SEARCH_URL.format(keyword=keyword)
            if page_num > 1:
                url += f"&page={page_num}"

            logger.info("Fetching page %d for keyword '%s'", page_num, keyword)
            await page.goto(url, wait_until="networkidle", timeout=30_000)

            # Brief pause to let JS render
            await page.wait_for_timeout(1500)

            prices, sellers = await _parse_page(page)
            all_prices.extend(prices)
            all_sellers.extend(sellers)

            if page_num < _PAGES_PER_KEYWORD:
                await asyncio.sleep(random.uniform(_DELAY_MIN, _DELAY_MAX))

    except Exception as exc:
        logger.error("Error crawling keyword '%s': %s", keyword, exc)
        return CrawlRecord(
            date=today,
            keyword=keyword,
            item_count=0,
            seller_count=0,
            avg_price=0.0,
        )
    finally:
        await context.close()

    item_count = len(all_prices)
    seller_count = len(set(all_sellers))
    avg_price = round(sum(all_prices) / item_count, 2) if item_count > 0 else 0.0

    logger.info(
        "Keyword '%s': items=%d, sellers=%d, avg_price=%.2f",
        keyword,
        item_count,
        seller_count,
        avg_price,
    )
    return CrawlRecord(
        date=today,
        keyword=keyword,
        item_count=item_count,
        seller_count=seller_count,
        avg_price=avg_price,
    )


# ---------------------------------------------------------------------------
# Batch crawl
# ---------------------------------------------------------------------------


async def _crawl_all_async(
    target_date: str, keywords: Union[list[str], None] = None
) -> list[CrawlRecord]:
    """Crawl all keywords sequentially using a single shared browser.

    Args:
        target_date: Date string "YYYY-MM-DD" for the records.
        keywords: Override keyword list (defaults to config.KEYWORDS).

    Returns:
        List of CrawlRecord, one per keyword.
    """
    kw_list = keywords or KEYWORDS
    records: list[CrawlRecord] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for i, kw in enumerate(kw_list):
                record = await _fetch_keyword_async(kw, browser)
                # Patch date in case the crawl ran past midnight
                records.append(CrawlRecord(**{**record, "date": target_date}))

                if i < len(kw_list) - 1:
                    delay = random.uniform(_DELAY_MIN, _DELAY_MAX)
                    logger.info("Sleeping %.1fs before next keyword…", delay)
                    await asyncio.sleep(delay)
        finally:
            await browser.close()

    return records


def crawl_all(
    target_date: Union[str, None] = None, keywords: Union[list[str], None] = None
) -> list[CrawlRecord]:
    """Synchronous wrapper: crawl all keywords and return records.

    Args:
        target_date: Date string "YYYY-MM-DD" (defaults to today).
        keywords: Override keyword list (defaults to config.KEYWORDS).

    Returns:
        List of CrawlRecord, one per keyword (zero-filled on failure).
    """
    td = target_date or utc_today_str()
    return asyncio.run(_crawl_all_async(td, keywords))


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------


def save_records(records: list[CrawlRecord]) -> None:
    """Upsert a list of CrawlRecords into SQLite (INSERT OR REPLACE).

    Duplicate (date, keyword) rows are replaced, preserving DB integrity.

    Args:
        records: CrawlRecord dicts to persist.
    """
    init_db()
    with get_db() as conn:
        for rec in records:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO crawl_records
                        (date, keyword, item_count, seller_count, avg_price)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        rec["date"],
                        rec["keyword"],
                        rec["item_count"],
                        rec["seller_count"],
                        rec["avg_price"],
                    ),
                )
            except sqlite3.Error as exc:
                logger.error("DB write failed for keyword '%s': %s", rec["keyword"], exc)
        conn.commit()
    logger.info("Saved %d record(s) to DB.", len(records))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl Xianyu AI keyword listings and store results."
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default=None,
        help="Crawl a single keyword instead of all. E.g. --keyword 'AI 副业'",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without writing to DB.",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()

    kw_list = [args.keyword] if args.keyword else None
    target = args.date or utc_today_str()

    logger.info("Starting crawl for date=%s, dry_run=%s", target, args.dry_run)
    records = crawl_all(target_date=target, keywords=kw_list)

    if args.dry_run:
        print("\n--- DRY RUN RESULTS ---")
        for r in records:
            print(
                f"  {r['keyword']:25s}  items={r['item_count']:4d}  "
                f"sellers={r['seller_count']:4d}  avg_price={r['avg_price']:7.2f}"
            )
        print("-----------------------\n")
    else:
        save_records(records)
        logger.info("Done.")
