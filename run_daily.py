"""run_daily.py — Orchestrate the full daily pipeline: crawl → analyze → render.

Entry point for both local runs and GitHub Actions.

CLI usage:
    .venv/bin/python3 run_daily.py                  # run for today
    .venv/bin/python3 run_daily.py --date 2026-03-06  # backfill a specific date
"""

import argparse
import logging
import sys

from analyzer import analyze
from crawler import crawl_all, save_records
from config import validate_runtime_environment, utc_today_str
from renderer import render

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(module)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


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

    # ── Step 1: Crawl ──────────────────────────────────────────────────────
    logger.info("[1/4] Crawling Xianyu…")
    records = crawl_all(target_date=target_date)

    total_items = sum(r["item_count"] for r in records)
    failed = [r["keyword"] for r in records if r["item_count"] == 0]
    logger.info(
        "Crawl complete: %d keywords, %d total items, %d failed.",
        len(records),
        total_items,
        len(failed),
    )
    if failed:
        logger.warning("Zero-item keywords (written as 0-records): %s", failed)

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

    # ── Step 4: Render ─────────────────────────────────────────────────────
    logger.info("[4/4] Rendering output files…")
    idx_png, daily_png, wkly_png, txt_path = render(result)

    logger.info("=== Done ===")
    for png in (idx_png, daily_png, wkly_png):
        logger.info("PNG  → %s", png)
    logger.info("Text → %s", txt_path)

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
