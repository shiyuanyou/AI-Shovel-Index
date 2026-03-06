"""preview_all.py — Generate all three card PNGs per status for visual inspection.

Usage:
    .venv/bin/python3 preview_all.py

Output goes to tests/fixtures/preview/ so it doesn't pollute the normal
fixture output directory.
"""

import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent))

from config import AnalysisResult, DailyRankingEntry, RankingEntry
from renderer import render

PREVIEW_DIR = Path(__file__).parent / "tests" / "fixtures" / "preview"

# Shared daily_rankings sample used across all scenarios
_SAMPLE_DAILY: List[DailyRankingEntry] = [
    DailyRankingEntry(keyword="Sora 教程", delta=45, pct=0.45),
    DailyRankingEntry(keyword="AI 副业", delta=28, pct=0.28),
    DailyRankingEntry(keyword="ChatGPT 教程", delta=5, pct=0.05),
    DailyRankingEntry(keyword="Claude 教程", delta=-8, pct=-0.08),
    DailyRankingEntry(keyword="Midjourney 教程", delta=-22, pct=-0.22),
    DailyRankingEntry(keyword="AI 变现", delta=-30, pct=-0.30),
]

SCENARIOS: List[AnalysisResult] = [
    AnalysisResult(
        date="2026-03-06",
        status="cold",
        index=8.0,
        warming_up=False,
        week_delta=-3.2,
        rankings=[
            RankingEntry(keyword="ChatGPT 教程", growth=-0.42),
            RankingEntry(keyword="AI 副业", growth=-0.38),
            RankingEntry(keyword="Midjourney 教程", growth=-0.25),
            RankingEntry(keyword="Sora 教程", growth=-0.18),
            RankingEntry(keyword="Claude 教程", growth=-0.10),
            RankingEntry(keyword="AI 变现", growth=-0.05),
        ],
        daily_rankings=_SAMPLE_DAILY,
    ),
    AnalysisResult(
        date="2026-03-06",
        status="early",
        index=28.0,
        warming_up=True,
        week_delta=0.0,
        rankings=[
            RankingEntry(keyword="AI 副业", growth=0.12),
            RankingEntry(keyword="ChatGPT 教程", growth=0.08),
            RankingEntry(keyword="Claude 教程", growth=0.03),
            RankingEntry(keyword="Midjourney 教程", growth=-0.04),
            RankingEntry(keyword="Stable Diffusion 教程", growth=-0.09),
            RankingEntry(keyword="AI 变现", growth=-0.14),
        ],
        daily_rankings=_SAMPLE_DAILY,
    ),
    AnalysisResult(
        date="2026-03-06",
        status="rising",
        index=51.0,
        warming_up=False,
        week_delta=7.3,
        rankings=[
            RankingEntry(keyword="Sora 教程", growth=0.38),
            RankingEntry(keyword="AI 副业", growth=0.31),
            RankingEntry(keyword="Claude 教程", growth=0.19),
            RankingEntry(keyword="ChatGPT 教程", growth=0.08),
            RankingEntry(keyword="AI 变现", growth=0.02),
            RankingEntry(keyword="Midjourney 教程", growth=-0.06),
        ],
        daily_rankings=_SAMPLE_DAILY,
    ),
    AnalysisResult(
        date="2026-03-06",
        status="speculation",
        index=67.0,
        warming_up=False,
        week_delta=12.5,
        rankings=[
            RankingEntry(keyword="Sora 教程", growth=0.52),
            RankingEntry(keyword="AI 副业", growth=0.31),
            RankingEntry(keyword="ChatGPT 教程", growth=0.08),
            RankingEntry(keyword="Claude 教程", growth=0.05),
            RankingEntry(keyword="Midjourney 教程", growth=-0.10),
            RankingEntry(keyword="AI 变现", growth=-0.16),
        ],
        daily_rankings=_SAMPLE_DAILY,
    ),
    AnalysisResult(
        date="2026-03-06",
        status="bubble",
        index=88.0,
        warming_up=False,
        week_delta=21.0,
        rankings=[
            RankingEntry(keyword="Sora 教程", growth=1.24),
            RankingEntry(keyword="AI 副业", growth=0.97),
            RankingEntry(keyword="ChatGPT 教程", growth=0.85),
            RankingEntry(keyword="Claude 教程", growth=0.71),
            RankingEntry(keyword="AI 变现", growth=0.63),
            RankingEntry(keyword="Midjourney 教程", growth=0.44),
        ],
        daily_rankings=_SAMPLE_DAILY,
    ),
]

if __name__ == "__main__":
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for s in SCENARIOS:
        idx_png, daily_png, wkly_png, txt = render(s, output_dir=PREVIEW_DIR)
        # Rename so all scenario files coexist
        status = s["status"]
        idx_png.rename(PREVIEW_DIR / f"card1_index_{status}.png")
        daily_png.rename(PREVIEW_DIR / f"card2_daily_{status}.png")
        wkly_png.rename(PREVIEW_DIR / f"card3_weekly_{status}.png")
        print(
            f"  [{status:12s}]  index={s['index']:5.1f}  delta={s['week_delta']:+.1f}"
            f"  → card1–3_{status}.png"
        )
    print(f"\nAll previews saved to: {PREVIEW_DIR}")
