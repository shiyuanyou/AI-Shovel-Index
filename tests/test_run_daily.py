"""Tests for run_daily.py logging and crawl health behavior."""

from pathlib import Path

import logging

import run_daily


SAMPLE_RECORDS = [
    {
        "date": "2026-03-06",
        "keyword": "Sora 教程",
        "item_count": 42,
        "seller_count": 18,
        "avg_price": 29.9,
    },
    {
        "date": "2026-03-06",
        "keyword": "AI 副业",
        "item_count": 0,
        "seller_count": 0,
        "avg_price": 0.0,
    },
    {
        "date": "2026-03-06",
        "keyword": "ChatGPT 教程",
        "item_count": 0,
        "seller_count": 0,
        "avg_price": 0.0,
    },
    {
        "date": "2026-03-06",
        "keyword": "Claude 教程",
        "item_count": 11,
        "seller_count": 6,
        "avg_price": 39.0,
    },
]


def test_summarize_crawl_computes_failure_ratio() -> None:
    summary = run_daily._summarize_crawl(SAMPLE_RECORDS)

    assert summary["total_keywords"] == 4
    assert summary["failure_count"] == 2
    assert summary["total_items"] == 53
    assert summary["failure_ratio"] == 0.5
    assert summary["failed_keywords"] == ["AI 副业", "ChatGPT 教程"]


def test_log_crawl_health_emits_error_for_systemic_failures(caplog) -> None:
    summary = run_daily._summarize_crawl(SAMPLE_RECORDS)

    with caplog.at_level(logging.INFO):
        run_daily._log_crawl_health(summary)

    assert "CRAWL_SUMMARY total_keywords=4 total_items=53 failed_keywords=2 failure_ratio=0.50" in caplog.text
    assert "CRAWL_HEALTH degraded failure_ratio=0.50 threshold=0.50" in caplog.text
    assert "Zero-item keywords (written as 0-records)" in caplog.text


def test_run_logs_analysis_and_output_summaries(monkeypatch, tmp_path: Path, caplog) -> None:
    index_png = tmp_path / "card1_index_2026_03_06.png"
    daily_png = tmp_path / "card2_daily_2026_03_06.png"
    weekly_png = tmp_path / "card3_weekly_2026_03_06.png"
    txt_path = tmp_path / "post.txt"

    for path in (index_png, daily_png, weekly_png, txt_path):
        path.write_text("ok", encoding="utf-8")

    monkeypatch.setattr(run_daily, "validate_runtime_environment", lambda: None)
    monkeypatch.setattr(run_daily, "crawl_all", lambda target_date: SAMPLE_RECORDS)
    monkeypatch.setattr(run_daily, "save_records", lambda records: None)
    monkeypatch.setattr(
        run_daily,
        "analyze",
        lambda _target_date: {
            "date": "2026-03-06",
            "index": 67.0,
            "status": "speculation",
            "rankings": [],
            "daily_rankings": [],
            "warming_up": False,
            "week_delta": 12.5,
        },
    )
    monkeypatch.setattr(
        run_daily,
        "render",
        lambda _result: (index_png, daily_png, weekly_png, txt_path),
    )

    with caplog.at_level(logging.INFO):
        run_daily.run("2026-03-06")

    assert "RUN_CONTEXT target_date=2026-03-06" in caplog.text
    assert "ANALYSIS_SUMMARY index=67.00 status=speculation warming_up=False week_delta=12.50" in caplog.text
    assert f"OUTPUT_SUMMARY card1={index_png} card2={daily_png} card3={weekly_png} post={txt_path}" in caplog.text
