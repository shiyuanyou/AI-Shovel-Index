"""analyzer.py — Read crawl records from DB and compute the daily index.

Data flow:
    SQLite (crawl_records) → get_records() → compute_index() → AnalysisResult

No external dependencies; uses only stdlib + config.
"""

import logging
import sqlite3
from collections import defaultdict
from datetime import date, timedelta

from config import (
    AnalysisResult,
    CrawlRecord,
    HISTORY_DAYS,
    INDEX_MAX,
    INDEX_SCALE,
    KEYWORDS,
    RankingEntry,
    STATUS_THRESHOLDS,
    WEIGHT_ITEMS,
    WEIGHT_SELLERS,
    get_db,
    init_db,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB read
# ---------------------------------------------------------------------------


def get_records(target_date: str, days: int = HISTORY_DAYS + 1) -> list[CrawlRecord]:
    """Return crawl records for the most recent `days` days up to and including target_date.

    Args:
        target_date: Upper bound date string "YYYY-MM-DD" (inclusive).
        days: How many days of history to fetch (default: HISTORY_DAYS + 1 to include today).

    Returns:
        List of CrawlRecord dicts ordered by date ascending.
    """
    end = date.fromisoformat(target_date)
    start = end - timedelta(days=days - 1)
    start_str = start.isoformat()

    init_db()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT date, keyword, item_count, seller_count, avg_price
            FROM crawl_records
            WHERE date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (start_str, target_date),
        ).fetchall()

    return [
        CrawlRecord(
            date=row["date"],
            keyword=row["keyword"],
            item_count=row["item_count"],
            seller_count=row["seller_count"],
            avg_price=row["avg_price"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Index computation
# ---------------------------------------------------------------------------


def get_status(index: float) -> str:
    """Map a numeric index value to its status label.

    Args:
        index: Float in range [0.0, 100.0].

    Returns:
        Status string: "cold" | "early" | "rising" | "speculation" | "bubble".
    """
    for threshold, label in STATUS_THRESHOLDS:
        if index >= threshold:
            return label
    return "cold"


def _mean(values: list[float]) -> float:
    """Return arithmetic mean; returns 0.0 for empty list."""
    return sum(values) / len(values) if values else 0.0


def compute_index(records: list[CrawlRecord], today: str) -> AnalysisResult:
    """Compute the daily AI Shovel Index from crawl records.

    Algorithm:
        For each keyword:
            - Separate today's record from the historical baseline (past ≤7 days).
            - growth_items   = today_items   / mean(history_items)   (1.0 if no history)
            - growth_sellers = today_sellers / mean(history_sellers) (1.0 if no history)
            - kw_score = (growth_items * WEIGHT_ITEMS + growth_sellers * WEIGHT_SELLERS) * INDEX_SCALE
        Final index = mean(kw_scores), clamped to [0, INDEX_MAX].
        warming_up = True when distinct historical days < HISTORY_DAYS.

    Args:
        records: All CrawlRecord rows for the relevant date window.
        today: The target date string "YYYY-MM-DD".

    Returns:
        AnalysisResult dict.
    """
    # Bucket records by keyword, then split today vs history
    today_by_kw: dict[str, CrawlRecord] = {}
    history_by_kw: dict[str, list[CrawlRecord]] = defaultdict(list)

    for rec in records:
        if rec["date"] == today:
            today_by_kw[rec["keyword"]] = rec
        else:
            history_by_kw[rec["keyword"]].append(rec)

    # Determine how many distinct historical days exist (across all keywords)
    historical_dates: set[str] = {r["date"] for r in records if r["date"] != today}
    warming_up: bool = len(historical_dates) < HISTORY_DAYS

    if warming_up:
        logger.warning(
            "Cold start: only %d historical day(s) available (need %d).",
            len(historical_dates),
            HISTORY_DAYS,
        )

    kw_scores: list[float] = []
    rankings: list[RankingEntry] = []

    # Use configured keywords as the canonical set; fall back gracefully if missing
    active_keywords = list(today_by_kw.keys()) or KEYWORDS

    for kw in active_keywords:
        today_rec = today_by_kw.get(kw)
        if today_rec is None:
            logger.warning("No today record for keyword '%s', skipping.", kw)
            continue

        hist = history_by_kw.get(kw, [])
        avg_hist_items = _mean([r["item_count"] for r in hist]) if hist else 0.0
        avg_hist_sellers = _mean([r["seller_count"] for r in hist]) if hist else 0.0

        # If no history exists, treat growth as 1.0 (neutral baseline)
        growth_items = (
            today_rec["item_count"] / avg_hist_items if avg_hist_items > 0 else 1.0
        )
        growth_sellers = (
            today_rec["seller_count"] / avg_hist_sellers
            if avg_hist_sellers > 0
            else 1.0
        )

        # Combined growth ratio (used for ranking display)
        combined_growth = growth_items * WEIGHT_ITEMS + growth_sellers * WEIGHT_SELLERS

        kw_score = combined_growth * INDEX_SCALE
        kw_scores.append(kw_score)

        rankings.append(
            RankingEntry(keyword=kw, growth=round(combined_growth - 1.0, 4))
        )

    # Aggregate
    raw_index = _mean(kw_scores) if kw_scores else 0.0
    final_index = round(min(raw_index, INDEX_MAX), 2)

    # Sort rankings by growth descending
    rankings.sort(key=lambda e: e["growth"], reverse=True)

    logger.info(
        "Index computed for %s: %.2f (%s), warming_up=%s",
        today,
        final_index,
        get_status(final_index),
        warming_up,
    )

    return AnalysisResult(
        date=today,
        index=final_index,
        status=get_status(final_index),
        rankings=rankings,
        warming_up=warming_up,
    )


# ---------------------------------------------------------------------------
# Convenience entry point (used by run_daily.py)
# ---------------------------------------------------------------------------


def analyze(target_date: str) -> AnalysisResult:
    """Load records and compute the index for target_date in one call.

    Args:
        target_date: Date string "YYYY-MM-DD".

    Returns:
        AnalysisResult dict.
    """
    records = get_records(target_date)
    return compute_index(records, target_date)
