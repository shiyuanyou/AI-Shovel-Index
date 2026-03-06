"""Tests for the deployment smoke-test helper."""

from pathlib import Path

from PIL import Image

import smoke_test


def test_build_smoke_result_has_active_card_data() -> None:
    result = smoke_test.build_smoke_result()

    assert result["status"] == "speculation"
    assert len(result["rankings"]) >= 4
    assert len(result["daily_rankings"]) >= 4
    assert result["warming_up"] is False


def test_run_smoke_test_renders_and_verifies_images(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[Path] = []

    def fake_validate_runtime_environment() -> None:
        calls.append(Path("validated"))

    def fake_render(_result, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        index_png = output_dir / "card1_index_2026_03_06.png"
        daily_png = output_dir / "card2_daily_2026_03_06.png"
        weekly_png = output_dir / "card3_weekly_2026_03_06.png"
        txt_path = output_dir / "post.txt"

        for image_path in (index_png, daily_png, weekly_png):
            Image.new("RGB", (16, 16), color="white").save(image_path)
        txt_path.write_text("smoke ok", encoding="utf-8")
        return index_png, daily_png, weekly_png, txt_path

    monkeypatch.setattr(smoke_test, "validate_runtime_environment", fake_validate_runtime_environment)
    monkeypatch.setattr(smoke_test, "render", fake_render)

    paths = smoke_test.run_smoke_test(tmp_path)

    assert calls == [Path("validated")]
    for path in paths:
        assert path.exists()
