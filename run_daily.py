"""run_daily.py — Orchestrate the full daily pipeline: crawl → analyze → render.

Entry point for both local runs and GitHub Actions.

CLI usage:
    .venv/bin/python3 run_daily.py                  # run for today
    .venv/bin/python3 run_daily.py --date 2026-03-06  # backfill a specific date
"""

import argparse
import logging
import sys

from typing import Any

from analyzer import analyze
from crawler import crawl_all, save_records
from config import (
    CRAWL_FAILURE_ERROR_RATIO,
    CRAWL_FAILURE_WARN_RATIO,
    validate_runtime_environment,
    utc_today_str,
)
from renderer import render

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(module)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _summarize_crawl(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a crawl health summary for log output and alerting."""
    total_keywords = len(records)
    failed_keywords = [record["keyword"] for record in records if record["item_count"] == 0]
    total_items = sum(int(record["item_count"]) for record in records)
    failure_count = len(failed_keywords)
    failure_ratio = (failure_count / total_keywords) if total_keywords else 0.0
    return {
        "total_keywords": total_keywords,
        "failed_keywords": failed_keywords,
        "failure_count": failure_count,
        "failure_ratio": failure_ratio,
        "total_items": total_items,
    }


def _log_crawl_health(summary: dict[str, Any]) -> None:
    """Emit structured crawl health logs so cloud failures stand out quickly."""
    logger.info(
        "CRAWL_SUMMARY total_keywords=%d total_items=%d failed_keywords=%d failure_ratio=%.2f",
        summary["total_keywords"],
        summary["total_items"],
        summary["failure_count"],
        summary["failure_ratio"],
    )

    failed_keywords = summary["failed_keywords"]
    if failed_keywords:
        logger.warning("Zero-item keywords (written as 0-records): %s", failed_keywords)

    if summary["failure_ratio"] >= CRAWL_FAILURE_ERROR_RATIO:
        logger.error(
            "CRAWL_HEALTH degraded failure_ratio=%.2f threshold=%.2f failed_keywords=%s",
            summary["failure_ratio"],
            CRAWL_FAILURE_ERROR_RATIO,
            failed_keywords,
        )
    elif summary["failure_ratio"] >= CRAWL_FAILURE_WARN_RATIO:
        logger.warning(
            "CRAWL_HEALTH warning failure_ratio=%.2f threshold=%.2f failed_keywords=%s",
            summary["failure_ratio"],
            CRAWL_FAILURE_WARN_RATIO,
            failed_keywords,
        )


def run(target_date: str) -> None:
    """Execute the full pipeline for a given date.

    Steps:
        1. Crawl all KEYWORDS on Xianyu → list[CrawlRecord]
        2. Persist records to SQLite
        3. Analyze records → AnalysisResult
        4. Render PNG + post.txt

    Args:
        target_date: Date string "YYYY-MM-DD" to process.
    """
    validate_runtime_environment()
    logger.info("=== AI Shovel Index daily run — %s ===", target_date)
    logger.info("RUN_CONTEXT target_date=%s", target_date)

    # ── Step 1: Crawl ──────────────────────────────────────────────────────
    logger.info("[1/4] Crawling Xianyu…")
    records = crawl_all(target_date=target_date)

    crawl_summary = _summarize_crawl(records)
    logger.info(
        "Crawl complete: %d keywords, %d total items, %d failed.",
        crawl_summary["total_keywords"],
        crawl_summary["total_items"],
        crawl_summary["failure_count"],
    )
    _log_crawl_health(crawl_summary)

    # ── Step 2: Persist ────────────────────────────────────────────────────
    logger.info("[2/4] Saving records to DB…")
    save_records(records)

    # ── Step 3: Analyze ────────────────────────────────────────────────────
    logger.info("[3/4] Analyzing…")
    result = analyze(target_date)
    logger.info(
        "Index: %.2f  Status: %s  warming_up: %s",
        result["index"],
        result["status"],
        result["warming_up"],
    )
    logger.info(
        "ANALYSIS_SUMMARY index=%.2f status=%s warming_up=%s week_delta=%.2f",
        result["index"],
        result["status"],
        result["warming_up"],
        result["week_delta"],
    )

    # ── Step 4: Render ─────────────────────────────────────────────────────
    logger.info("[4/4] Rendering output files…")
    idx_png, daily_png, wkly_png, txt_path = render(result)

    logger.info("=== Done ===")
    for png in (idx_png, daily_png, wkly_png):
        logger.info("PNG  → %s", png)
    logger.info("Text → %s", txt_path)
    logger.info(
        "OUTPUT_SUMMARY card1=%s card2=%s card3=%s post=%s",
        idx_png,
        daily_png,
        wkly_png,
        txt_path,
    )

    # Print final paths to stdout (for CI artifact collection)
    print(f"Card1 (index):   {idx_png}")
    print(f"Card2 (daily):   {daily_png}")
    print(f"Card3 (weekly):  {wkly_png}")
    print(f"TXT:             {txt_path}")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI Shovel Index daily pipeline.")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date in YYYY-MM-DD format. Defaults to today.",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    target = args.date or utc_today_str()

    try:
        run(target)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)
