"""tests/test_renderer.py — Unit tests for renderer.py.

Writes test output to tests/fixtures/output/ for visual inspection.
Tests verify file existence, image dimensions, and post.txt content.
"""

from pathlib import Path

import pytest
from PIL import Image

from config import AnalysisResult, IMAGE_HEIGHT, IMAGE_WIDTH, RankingEntry
from renderer import render


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_OUTPUT = Path(__file__).parent / "fixtures" / "output"


def _make_result(
    status: str = "speculation",
    index: float = 67.0,
    warming_up: bool = False,
    date: str = "2026-03-06",
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
        warming_up=warming_up,
    )


# ---------------------------------------------------------------------------
# Output file generation
# ---------------------------------------------------------------------------


class TestRenderOutputFiles:
    def test_png_file_created(self, tmp_path: Path) -> None:
        result = _make_result()
        png_path, _ = render(result, output_dir=tmp_path)
        assert png_path.exists()
        assert png_path.suffix == ".png"

    def test_txt_file_created(self, tmp_path: Path) -> None:
        result = _make_result()
        _, txt_path = render(result, output_dir=tmp_path)
        assert txt_path.exists()
        assert txt_path.name == "post.txt"

    def test_png_filename_contains_date(self, tmp_path: Path) -> None:
        result = _make_result(date="2026-03-06")
        png_path, _ = render(result, output_dir=tmp_path)
        assert "2026_03_06" in png_path.name

    def test_returns_correct_paths(self, tmp_path: Path) -> None:
        result = _make_result()
        png_path, txt_path = render(result, output_dir=tmp_path)
        assert isinstance(png_path, Path)
        assert isinstance(txt_path, Path)


# ---------------------------------------------------------------------------
# Image dimensions
# ---------------------------------------------------------------------------


class TestImageDimensions:
    def test_image_size_1080x1080(self, tmp_path: Path) -> None:
        result = _make_result()
        png_path, _ = render(result, output_dir=tmp_path)
        img = Image.open(png_path)
        assert img.size == (IMAGE_WIDTH, IMAGE_HEIGHT)
        assert img.size == (1080, 1080)

    def test_image_mode_rgb(self, tmp_path: Path) -> None:
        result = _make_result()
        png_path, _ = render(result, output_dir=tmp_path)
        img = Image.open(png_path)
        assert img.mode == "RGB"


# ---------------------------------------------------------------------------
# Warming-up flag
# ---------------------------------------------------------------------------


class TestWarmingUp:
    def test_warming_up_renders_without_error(self, tmp_path: Path) -> None:
        result = _make_result(warming_up=True, index=50.0, status="rising")
        png_path, txt_path = render(result, output_dir=tmp_path)
        assert png_path.exists()
        assert txt_path.exists()

    def test_warming_up_notice_in_post_txt(self, tmp_path: Path) -> None:
        result = _make_result(warming_up=True)
        _, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "warming up" in content.lower()

    def test_no_warming_up_notice_when_false(self, tmp_path: Path) -> None:
        result = _make_result(warming_up=False)
        _, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "warming up" not in content.lower()


# ---------------------------------------------------------------------------
# post.txt content
# ---------------------------------------------------------------------------


class TestPostTxt:
    def test_score_in_post(self, tmp_path: Path) -> None:
        result = _make_result(index=67.0)
        _, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "67" in content

    def test_status_in_post(self, tmp_path: Path) -> None:
        result = _make_result(status="speculation")
        _, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "SPECULATION" in content

    def test_date_in_post(self, tmp_path: Path) -> None:
        result = _make_result(date="2026-03-06")
        _, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "2026-03-06" in content

    def test_keywords_in_post(self, tmp_path: Path) -> None:
        result = _make_result()
        _, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "Sora 教程" in content

    def test_hashtags_in_post(self, tmp_path: Path) -> None:
        result = _make_result()
        _, txt_path = render(result, output_dir=tmp_path)
        content = txt_path.read_text(encoding="utf-8")
        assert "#AIshovelindex" in content


# ---------------------------------------------------------------------------
# All five status colours render without error
# ---------------------------------------------------------------------------


class TestAllStatuses:
    @pytest.mark.parametrize(
        "status,index",
        [
            ("cold", 10.0),
            ("early", 30.0),
            ("rising", 50.0),
            ("speculation", 70.0),
            ("bubble", 90.0),
        ],
    )
    def test_status_renders(self, status: str, index: float, tmp_path: Path) -> None:
        result = _make_result(status=status, index=index)
        png_path, _ = render(result, output_dir=tmp_path)
        assert png_path.exists()
        img = Image.open(png_path)
        assert img.size == (IMAGE_WIDTH, IMAGE_HEIGHT)


# ---------------------------------------------------------------------------
# Visual fixture — saves a real render to tests/fixtures/output/ for inspection
# ---------------------------------------------------------------------------


def test_save_fixture_for_visual_inspection() -> None:
    """Generate a real render into fixtures/output/ for manual review.

    Not a strict assertion test — just ensures the file is produced.
    """
    FIXTURE_OUTPUT.mkdir(parents=True, exist_ok=True)
    result = _make_result(status="speculation", index=67.0, warming_up=False)
    png_path, txt_path = render(result, output_dir=FIXTURE_OUTPUT)
    assert png_path.exists()
    assert txt_path.exists()
