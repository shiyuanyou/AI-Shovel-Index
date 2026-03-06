"""tests/test_renderer.py — Unit tests for renderer.py.

Writes test output to tests/fixtures/output/ for visual inspection.
Tests verify file existence, image dimensions, and post.txt content.
Three card PNGs are verified: index (card1), daily (card2), weekly (card3).
"""

from pathlib import Path

import pytest
from PIL import Image

from config import (
    AUTHOR_HANDLE,
    AnalysisResult,
    DailyRankingEntry,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    RankingEntry,
)
from renderer import render

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_OUTPUT = Path(__file__).parent / "fixtures" / "output"

_SAMPLE_DAILY = [
    DailyRankingEntry(keyword="Sora 教程", delta=45, pct=0.45),
    DailyRankingEntry(keyword="AI 副业", delta=28, pct=0.28),
    DailyRankingEntry(keyword="ChatGPT 教程", delta=5, pct=0.05),
    DailyRankingEntry(keyword="Midjourney 教程", delta=-22, pct=-0.22),
]


def _make_result(
    status: str = "speculation",
    index: float = 67.0,
    warming_up: bool = False,
    date: str = "2026-03-06",
    week_delta: float = 5.0,
) -> AnalysisResult:
    return AnalysisResult(
        date=date,
        index=index,
        status=status,
        rankings=[
            RankingEntry(keyword="Sora 教程", growth=0.52),
            RankingEntry(keyword="AI 副业", growth=0.31),
            RankingEntry(keyword="ChatGPT 教程", growth=0.08),
            RankingEntry(keyword="Midjourney 教程", growth=-0.10),
        ],
        daily_rankings=_SAMPLE_DAILY,
        warming_up=warming_up,
        week_delta=week_delta,
    )


# ---------------------------------------------------------------------------
# Output file generation — 3 PNGs + 1 txt
# ---------------------------------------------------------------------------


class TestRenderOutputFiles:
    def test_returns_four_paths(self, tmp_path: Path) -> None:
        result = _make_result()
        paths = render(result, output_dir=tmp_path)
        assert len(paths) == 4

    def test_all_pngs_created(self, tmp_path: Path) -> None:
        result = _make_result()
        idx, daily, wkly, txt = render(result, output_dir=tmp_path)
        for p in (idx, daily, wkly):
            assert p.exists(), f"Missing PNG: {p}"
            assert p.suffix == ".png"

    def test_txt_file_created(self, tmp_path: Path) -> None:
        result = _make_result()
        *_, txt_path = render(result, output_dir=tmp_path)
        assert txt_path.exists()
        assert txt_path.name == "post.txt"

    def test_png_filenames_contain_date(self, tmp_path: Path) -> None:
        result = _make_result(date="2026-03-06")
        idx, daily, wkly, _ = render(result, output_dir=tmp_path)
        for p in (idx, daily, wkly):
            assert "2026_03_06" in p.name, f"Date not in filename: {p.name}"

    def test_png_filename_prefixes(self, tmp_path: Path) -> None:
        result = _make_result(date="2026-03-06")
        idx, daily, wkly, _ = render(result, output_dir=tmp_path)
        assert idx.name.startswith("card1_index_")
        assert daily.name.startswith("card2_daily_")
        assert wkly.name.startswith("card3_weekly_")

    def test_returns_path_objects(self, tmp_path: Path) -> None:
        result = _make_result()
        for p in render(result, output_dir=tmp_path):
            assert isinstance(p, Path)


# ---------------------------------------------------------------------------
# Image dimensions — all 3 cards must be 1080×1080
# ---------------------------------------------------------------------------


class TestImageDimensions:
    def test_all_cards_1080x1080(self, tmp_path: Path) -> None:
        result = _make_result()
        idx, daily, wkly, _ = render(result, output_dir=tmp_path)
        for p in (idx, daily, wkly):
            img = Image.open(p)
            assert img.size == (IMAGE_WIDTH, IMAGE_HEIGHT), f"{p.name}: {img.size}"
            assert img.size == (1080, 1080)

    def test_all_cards_rgb_mode(self, tmp_path: Path) -> None:
        result = _make_result()
        idx, daily, wkly, _ = render(result, output_dir=tmp_path)
        for p in (idx, daily, wkly):
            img = Image.open(p)
            assert img.mode == "RGB", f"{p.name}: mode={img.mode}"


# ---------------------------------------------------------------------------
# Warming-up flag
# ---------------------------------------------------------------------------


class TestWarmingUp:
    def test_warming_up_renders_without_error(self, tmp_path: Path) -> None:
        result = _make_result(warming_up=True, index=50.0, status="rising", week_delta=0.0)
        paths = render(result, output_dir=tmp_path)
        for p in paths:
            assert p.exists()

    def test_warming_up_notice_in_post_txt(self, tmp_path: Path) -> None:
        result = _make_result(warming_up=True, week_delta=0.0)
        *_, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "warming up" in content.lower()

    def test_no_warming_up_notice_when_false(self, tmp_path: Path) -> None:
        result = _make_result(warming_up=False)
        *_, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "warming up" not in content.lower()


# ---------------------------------------------------------------------------
# post.txt content
# ---------------------------------------------------------------------------


class TestPostTxt:
    def test_score_in_post(self, tmp_path: Path) -> None:
        result = _make_result(index=67.0)
        *_, txt_path = render(result, output_dir=tmp_path)
        assert "67" in txt_path.read_text(encoding="utf-8")

    def test_status_in_post(self, tmp_path: Path) -> None:
        result = _make_result(status="speculation")
        *_, txt_path = render(result, output_dir=tmp_path)
        assert "SPECULATION" in txt_path.read_text(encoding="utf-8")

    def test_date_in_post(self, tmp_path: Path) -> None:
        result = _make_result(date="2026-03-06")
        *_, txt_path = render(result, output_dir=tmp_path)
        assert "2026-03-06" in txt_path.read_text(encoding="utf-8")

    def test_keywords_in_post(self, tmp_path: Path) -> None:
        result = _make_result()
        *_, txt_path = render(result, output_dir=tmp_path)
        assert "Sora 教程" in txt_path.read_text(encoding="utf-8")

    def test_hashtags_in_post(self, tmp_path: Path) -> None:
        result = _make_result()
        *_, txt_path = render(result, output_dir=tmp_path)
        assert "#AIshovelindex" in txt_path.read_text(encoding="utf-8")

    def test_author_handle_in_post(self, tmp_path: Path) -> None:
        result = _make_result()
        *_, txt_path = render(result, output_dir=tmp_path)
        assert AUTHOR_HANDLE in txt_path.read_text(encoding="utf-8")

    def test_week_delta_in_post_when_not_warming_up(self, tmp_path: Path) -> None:
        result = _make_result(warming_up=False, week_delta=7.3)
        *_, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "7.3" in content

    def test_week_delta_absent_when_warming_up(self, tmp_path: Path) -> None:
        result = _make_result(warming_up=True, week_delta=0.0)
        *_, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        # No delta line when warming_up
        assert "vs last week" not in content


# ---------------------------------------------------------------------------
# Cooling-only scenario — card3 must render with data
# ---------------------------------------------------------------------------


class TestCoolingOnly:
    def test_all_negative_renders_without_error(self, tmp_path: Path) -> None:
        result = AnalysisResult(
            date="2026-03-06",
            index=8.0,
            status="cold",
            rankings=[
                RankingEntry(keyword="Midjourney 教程", growth=-0.25),
                RankingEntry(keyword="Stable Diffusion 教程", growth=-0.18),
            ],
            daily_rankings=[
                DailyRankingEntry(keyword="Midjourney 教程", delta=-20, pct=-0.25),
                DailyRankingEntry(keyword="Stable Diffusion 教程", delta=-15, pct=-0.18),
            ],
            warming_up=False,
            week_delta=-4.0,
        )
        idx, daily, wkly, txt = render(result, output_dir=tmp_path)
        for p in (idx, daily, wkly, txt):
            assert p.exists()


# ---------------------------------------------------------------------------
# All five status colours render without error
# ---------------------------------------------------------------------------


class TestAllStatuses:
    @pytest.mark.parametrize(
        "status,index,delta",
        [
            ("cold", 10.0, -5.0),
            ("early", 30.0, 2.0),
            ("rising", 50.0, 7.0),
            ("speculation", 70.0, 12.0),
            ("bubble", 90.0, 20.0),
        ],
    )
    def test_status_renders_all_cards(
        self, status: str, index: float, delta: float, tmp_path: Path
    ) -> None:
        result = _make_result(status=status, index=index, week_delta=delta)
        idx, daily, wkly, _ = render(result, output_dir=tmp_path)
        for p in (idx, daily, wkly):
            assert p.exists()
            img = Image.open(p)
            assert img.size == (IMAGE_WIDTH, IMAGE_HEIGHT)


# ---------------------------------------------------------------------------
# Daily signal card — empty daily_rankings renders without error
# ---------------------------------------------------------------------------


class TestDailySignalCard:
    def test_empty_daily_rankings_renders(self, tmp_path: Path) -> None:
        """Card 2 must render gracefully when no daily comparison data is available."""
        result = AnalysisResult(
            date="2026-03-06",
            index=50.0,
            status="rising",
            rankings=[RankingEntry(keyword="AI 副业", growth=0.20)],
            daily_rankings=[],
            warming_up=False,
            week_delta=3.0,
        )
        idx, daily, wkly, txt = render(result, output_dir=tmp_path)
        for p in (idx, daily, wkly, txt):
            assert p.exists()

    def test_daily_card_1080x1080(self, tmp_path: Path) -> None:
        result = _make_result()
        _, daily, _, _ = render(result, output_dir=tmp_path)
        img = Image.open(daily)
        assert img.size == (1080, 1080)


# ---------------------------------------------------------------------------
# Visual fixture — saves a real render to tests/fixtures/output/ for inspection
# ---------------------------------------------------------------------------


def test_save_fixture_for_visual_inspection() -> None:
    """Generate a real render into fixtures/output/ for manual review.

    Not a strict assertion test — just ensures all three cards are produced.
    """
    FIXTURE_OUTPUT.mkdir(parents=True, exist_ok=True)
    result = _make_result(status="rising", index=51.0, warming_up=False, week_delta=7.3)
    idx, daily, wkly, txt = render(result, output_dir=FIXTURE_OUTPUT)
    for p in (idx, daily, wkly, txt):
        assert p.exists()
