"""smoke_test.py - Render a known-good sample payload for deployment verification.

Usage:
    .venv/bin/python3 smoke_test.py
    .venv/bin/python3 smoke_test.py --output-dir output/smoke

This avoids crawling live data and verifies that the deployment environment can:
- import the project modules
- write to the configured runtime directories
- launch Playwright Chromium
- render all three active cards plus post.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from config import (
    AnalysisResult,
    DailyRankingEntry,
    OUTPUT_DIR,
    RankingEntry,
    validate_runtime_environment,
)
from renderer import render


def build_smoke_result() -> AnalysisResult:
    """Return a stable sample result that exercises all active templates."""
    return AnalysisResult(
        date="2026-03-06",
        index=67.0,
        status="speculation",
        rankings=[
            RankingEntry(keyword="Sora 教程", growth=0.52),
            RankingEntry(keyword="AI 副业", growth=0.31),
            RankingEntry(keyword="ChatGPT 教程", growth=0.08),
            RankingEntry(keyword="Claude 教程", growth=0.05),
            RankingEntry(keyword="Midjourney 教程", growth=-0.10),
            RankingEntry(keyword="AI 变现", growth=-0.16),
        ],
        daily_rankings=[
            DailyRankingEntry(keyword="Sora 教程", delta=45, pct=0.45),
            DailyRankingEntry(keyword="AI 副业", delta=28, pct=0.28),
            DailyRankingEntry(keyword="ChatGPT 教程", delta=5, pct=0.05),
            DailyRankingEntry(keyword="Claude 教程", delta=-8, pct=-0.08),
            DailyRankingEntry(keyword="Midjourney 教程", delta=-22, pct=-0.22),
            DailyRankingEntry(keyword="AI 变现", delta=-30, pct=-0.30),
        ],
        warming_up=False,
        week_delta=12.5,
    )


def run_smoke_test(output_dir: Path) -> tuple[Path, Path, Path, Path]:
    """Render the smoke-test payload and verify the PNGs open correctly."""
    validate_runtime_environment()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = render(build_smoke_result(), output_dir=output_dir)

    for image_path in paths[:3]:
        with Image.open(image_path) as image:
            image.verify()

    return paths


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render smoke-test output for deployment checks.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR / "smoke",
        help="Directory for smoke-test artifacts. Defaults to output/smoke.",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    index_png, daily_png, weekly_png, txt_path = run_smoke_test(args.output_dir)
    print(f"Smoke card1: {index_png}")
    print(f"Smoke card2: {daily_png}")
    print(f"Smoke card3: {weekly_png}")
    print(f"Smoke text:  {txt_path}")
