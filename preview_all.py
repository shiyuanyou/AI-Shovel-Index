"""preview_all.py — Generate one card PNG per status for visual inspection.

Usage:
    python3 preview_all.py

Output goes to tests/fixtures/preview/ so it doesn't pollute the normal
fixture output directory.
"""

import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent))

from config import AnalysisResult, RankingEntry
from renderer import render

PREVIEW_DIR = Path(__file__).parent / "tests" / "fixtures" / "preview"

SCENARIOS: List[AnalysisResult] = [
    AnalysisResult(
        date="2026-03-06",
        status="cold",
        index=8.0,
        warming_up=False,
        rankings=[
            RankingEntry(keyword="ChatGPT 教程", growth=-0.42),
            RankingEntry(keyword="AI 副业", growth=-0.38),
            RankingEntry(keyword="Midjourney 教程", growth=-0.25),
            RankingEntry(keyword="Sora 教程", growth=-0.18),
            RankingEntry(keyword="Claude 教程", growth=-0.10),
            RankingEntry(keyword="AI 变现", growth=-0.05),
        ],
    ),
    AnalysisResult(
        date="2026-03-06",
        status="early",
        index=28.0,
        warming_up=True,
        rankings=[
            RankingEntry(keyword="AI 副业", growth=0.12),
            RankingEntry(keyword="ChatGPT 教程", growth=0.08),
            RankingEntry(keyword="Claude 教程", growth=0.03),
            RankingEntry(keyword="Midjourney 教程", growth=-0.04),
            RankingEntry(keyword="Stable Diffusion 教程", growth=-0.09),
            RankingEntry(keyword="AI 变现", growth=-0.14),
        ],
    ),
    AnalysisResult(
        date="2026-03-06",
        status="rising",
        index=51.0,
        warming_up=False,
        rankings=[
            RankingEntry(keyword="Sora 教程", growth=0.38),
            RankingEntry(keyword="AI 副业", growth=0.31),
            RankingEntry(keyword="Claude 教程", growth=0.19),
            RankingEntry(keyword="ChatGPT 教程", growth=0.08),
            RankingEntry(keyword="AI 变现", growth=0.02),
            RankingEntry(keyword="Midjourney 教程", growth=-0.06),
        ],
    ),
    AnalysisResult(
        date="2026-03-06",
        status="speculation",
        index=67.0,
        warming_up=False,
        rankings=[
            RankingEntry(keyword="Sora 教程", growth=0.52),
            RankingEntry(keyword="AI 副业", growth=0.31),
            RankingEntry(keyword="ChatGPT 教程", growth=0.08),
            RankingEntry(keyword="Claude 教程", growth=0.05),
            RankingEntry(keyword="Midjourney 教程", growth=-0.10),
            RankingEntry(keyword="AI 变现", growth=-0.16),
        ],
    ),
    AnalysisResult(
        date="2026-03-06",
        status="bubble",
        index=88.0,
        warming_up=False,
        rankings=[
            RankingEntry(keyword="Sora 教程", growth=1.24),
            RankingEntry(keyword="AI 副业", growth=0.97),
            RankingEntry(keyword="ChatGPT 教程", growth=0.85),
            RankingEntry(keyword="Claude 教程", growth=0.71),
            RankingEntry(keyword="AI 变现", growth=0.63),
            RankingEntry(keyword="Midjourney 教程", growth=0.44),
        ],
    ),
]

if __name__ == "__main__":
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for s in SCENARIOS:
        png, txt = render(s, output_dir=PREVIEW_DIR)
        # Rename so all 5 files coexist (default name is index_YYYY_MM_DD.png)
        dest = PREVIEW_DIR / f"card_{s['status']}.png"
        png.rename(dest)
        print(f"  [{s['status']:12s}]  index={s['index']:5.1f}  → {dest.name}")
    print(f"\nAll previews saved to: {PREVIEW_DIR}")
