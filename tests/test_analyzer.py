"""tests/test_analyzer.py — Unit tests for analyzer.py.

Uses in-memory SQLite to avoid touching the real data/index.db.
All test data is constructed explicitly; no file I/O side effects.
"""

import sqlite3
from datetime import date, timedelta

import pytest

from analyzer import compute_index, get_records, get_status
from config import AnalysisResult, CrawlRecord, HISTORY_DAYS, INDEX_MAX


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    kw: str,
    date_str: str,
    item_count: int = 100,
    seller_count: int = 80,
    avg_price: float = 29.9,
) -> CrawlRecord:
    return CrawlRecord(
        date=date_str,
        keyword=kw,
        item_count=item_count,
        seller_count=seller_count,
        avg_price=avg_price,
    )


def _days_ago(n: int, anchor: str = "2026-03-06") -> str:
    d = date.fromisoformat(anchor) - timedelta(days=n)
    return d.isoformat()


TODAY = "2026-03-06"


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


class TestGetStatus:
    def test_cold(self) -> None:
        assert get_status(0.0) == "cold"
        assert get_status(19.9) == "cold"

    def test_early(self) -> None:
        assert get_status(20.0) == "early"
        assert get_status(39.9) == "early"

    def test_rising(self) -> None:
        assert get_status(40.0) == "rising"
        assert get_status(59.9) == "rising"

    def test_speculation(self) -> None:
        assert get_status(60.0) == "speculation"
        assert get_status(79.9) == "speculation"

    def test_bubble(self) -> None:
        assert get_status(80.0) == "bubble"
        assert get_status(100.0) == "bubble"

    def test_all_five_statuses_covered(self) -> None:
        statuses = {get_status(v) for v in [5, 25, 50, 70, 90]}
        assert statuses == {"cold", "early", "rising", "speculation", "bubble"}


# ---------------------------------------------------------------------------
# compute_index — cold start (< 7 days of history)
# ---------------------------------------------------------------------------


class TestColdStart:
    def test_single_day_warming_up_true(self) -> None:
        """Only today's data → warming_up must be True."""
        records = [_make_record("AI 副业", TODAY)]
        result = compute_index(records, TODAY)
        assert result["warming_up"] is True

    def test_single_day_index_is_baseline(self) -> None:
        """With no history, growth defaults to 1.0 → index = 1.0 * SCALE = 50.0."""
        records = [_make_record("AI 副业", TODAY, item_count=100, seller_count=80)]
        result = compute_index(records, TODAY)
        # growth = 1.0 (no history), score = 1.0 * 50 = 50.0
        assert result["index"] == pytest.approx(50.0)
        assert result["status"] == "rising"

    def test_partial_history_warming_up_true(self) -> None:
        """3 days of history (< 7) → warming_up True."""
        records = [_make_record("AI 副业", _days_ago(i)) for i in range(3, 0, -1)]
        records.append(_make_record("AI 副业", TODAY))
        result = compute_index(records, TODAY)
        assert result["warming_up"] is True

    def test_exactly_seven_days_not_warming_up(self) -> None:
        """Exactly 7 historical days → warming_up False."""
        records = [_make_record("AI 副业", _days_ago(i)) for i in range(7, 0, -1)]
        records.append(_make_record("AI 副业", TODAY))
        result = compute_index(records, TODAY)
        assert result["warming_up"] is False


# ---------------------------------------------------------------------------
# compute_index — normal operation
# ---------------------------------------------------------------------------


class TestNormalIndex:
    def _build_records(
        self,
        kw: str = "AI 副业",
        hist_items: int = 100,
        hist_sellers: int = 80,
        today_items: int = 150,
        today_sellers: int = 100,
    ) -> list[CrawlRecord]:
        records = [
            _make_record(
                kw, _days_ago(i), item_count=hist_items, seller_count=hist_sellers
            )
            for i in range(7, 0, -1)
        ]
        records.append(
            _make_record(kw, TODAY, item_count=today_items, seller_count=today_sellers)
        )
        return records

    def test_index_within_bounds(self) -> None:
        records = self._build_records()
        result = compute_index(records, TODAY)
        assert 0.0 <= result["index"] <= INDEX_MAX

    def test_index_clamped_at_100(self) -> None:
        """Extremely high growth should be clamped at 100."""
        records = self._build_records(
            hist_items=10, hist_sellers=10, today_items=10000, today_sellers=10000
        )
        result = compute_index(records, TODAY)
        assert result["index"] == INDEX_MAX

    def test_flat_growth_gives_fifty(self) -> None:
        """When today == history baseline, growth = 1.0 → index = 50.0."""
        records = self._build_records(
            hist_items=100, hist_sellers=80, today_items=100, today_sellers=80
        )
        result = compute_index(records, TODAY)
        assert result["index"] == pytest.approx(50.0)

    def test_growth_calculation_correct(self) -> None:
        """Manual spot-check of the formula."""
        # hist avg: items=100, sellers=80; today: items=200, sellers=120
        # growth_items = 2.0, growth_sellers = 1.5
        # combined = 2.0*0.6 + 1.5*0.4 = 1.2 + 0.6 = 1.8
        # score = 1.8 * 50 = 90.0
        records = self._build_records(
            hist_items=100, hist_sellers=80, today_items=200, today_sellers=120
        )
        result = compute_index(records, TODAY)
        assert result["index"] == pytest.approx(90.0)
        assert result["status"] == "bubble"

    def test_rankings_sorted_descending(self) -> None:
        """Rankings must be sorted by growth descending."""
        kw1_records = self._build_records("kw_high", hist_items=100, today_items=200)
        kw2_records = self._build_records("kw_low", hist_items=100, today_items=110)
        # re-date kw2 records to TODAY / past
        all_records = kw1_records + kw2_records
        result = compute_index(all_records, TODAY)
        growths = [e["growth"] for e in result["rankings"]]
        assert growths == sorted(growths, reverse=True)

    def test_missing_today_keyword_skipped(self) -> None:
        """Keywords with no today record are skipped gracefully."""
        records = [_make_record("AI 副业", _days_ago(i)) for i in range(7, 0, -1)]
        # No today record for "AI 副业"
        result = compute_index(records, TODAY)
        assert result["index"] == 0.0  # no active keywords

    def test_zero_history_items_no_crash(self) -> None:
        """Zero item_count in history should not cause ZeroDivisionError."""
        records = [
            _make_record("AI 副业", _days_ago(i), item_count=0, seller_count=0)
            for i in range(7, 0, -1)
        ]
        records.append(_make_record("AI 副业", TODAY, item_count=50, seller_count=30))
        result = compute_index(records, TODAY)
        # No history → growth = 1.0 baseline
        assert result["index"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# compute_index — result structure
# ---------------------------------------------------------------------------


class TestResultStructure:
    def test_required_keys_present(self) -> None:
        records = [_make_record("AI 副业", TODAY)]
        result = compute_index(records, TODAY)
        for key in ("date", "index", "status", "rankings", "warming_up"):
            assert key in result

    def test_date_passthrough(self) -> None:
        records = [_make_record("AI 副业", TODAY)]
        result = compute_index(records, TODAY)
        assert result["date"] == TODAY

    def test_ranking_entry_keys(self) -> None:
        records = [_make_record("AI 副业", TODAY)]
        result = compute_index(records, TODAY)
        if result["rankings"]:
            entry = result["rankings"][0]
            assert "keyword" in entry
            assert "growth" in entry
