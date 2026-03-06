"""renderer.py — Render AnalysisResult into three 1080×1080 PNGs and post.txt.

Card layout (all 1:1 square, optimised for social media):
    Card 1 — card_index.html   : core index gauge with week delta
    Card 2 — card_drivers.html : today vs yesterday signal (daily change per keyword)
    Card 3 — card_cooling.html : weekly brief — left column rising / right column cooling

The legacy card_weekly.html remains in the templates directory but is no longer
referenced by this module.  card.html (original single-card design) is also retained
for historical reference only.

Dependencies: jinja2, playwright
"""

import asyncio
import logging
import math
from pathlib import Path
from typing import Dict, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

from config import (
    AUTHOR_HANDLE,
    AnalysisResult,
    DailyRankingEntry,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    OUTPUT_DIR,
    RankingEntry,
    STATUS_COLORS,
    TEMPLATES_DIR,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase labels — human-readable version of status
# ---------------------------------------------------------------------------

_PHASE_LABELS: dict[str, str] = {
    "cold": "市场冷静",
    "early": "初步信号",
    "rising": "热度上升",
    "speculation": "投机阶段",
    "bubble": "泡沫预警",
}

# Chinese badge text for status pill — shown on all cards
_STATUS_BADGE: dict[str, str] = {
    "cold": "市场冷静",
    "early": "初步信号",
    "rising": "热度上升",
    "speculation": "投机阶段",
    "bubble": "泡沫预警",
}

# Card 3 驱动词摘要（中文）
_DRIVER_SUMMARIES: dict[str, str] = {
    "cold": "投机活动整体低迷。",
    "early": "教程需求初步浮现，值得持续观察。",
    "rising": "多个品类教程市场同步升温。",
    "speculation": "各 AI 细分领域投机需求信号强烈。",
    "bubble": "教程数量急剧扩张，可能进入泡沫区间。",
}

_COOLING_SUMMARIES: dict[str, str] = {
    "cold": "",
    "early": "",
    "rising": "部分话题热度下滑，资金转向新兴赛道。",
    "speculation": "市场轮动明显，资金追逐更新的关键词。",
    "bubble": "老牌 AI 教程品类出现早期饱和迹象。",
}

# Max drivers / cooling shown on Card 3
_MAX_DRIVERS = 4
_MAX_COOLING = 4

# Max keywords shown on Card 2 (daily signal)
_MAX_DAILY = 6

# SVG gauge geometry — Card 1
_GAUGE_RADIUS: int = 240
_GAUGE_CIRCUMFERENCE: float = math.pi * _GAUGE_RADIUS  # ≈ 753.98


def _arc_offset(index: float) -> float:
    """Compute SVG stroke-dashoffset for the gauge arc fill.

    When dashoffset == circumference the arc is invisible; when 0 it is full.
    Interpolated linearly from the 0–100 index value.

    Args:
        index: Index score in [0, 100].

    Returns:
        stroke-dashoffset value (float, rounded to 2 dp).
    """
    fraction = max(0.0, min(float(index), 100.0)) / 100.0
    return round(_GAUGE_CIRCUMFERENCE * (1.0 - fraction), 2)


def _bar_pct(growth: float) -> float:
    """Convert a growth ratio to a bar fill percentage in [0, 100].

    Positive: maps 0 → 0%, +2.0 → 100%.
    Negative: maps 0 → 0%, −1.0 → 100% (absolute value).
    """
    return round(min(abs(growth) / 2.0, 1.0) * 100, 1)


def _pct_str(growth: float) -> str:
    """Format growth ratio as a signed percentage string, e.g. '+52%' or '−10%'."""
    sign = "+" if growth >= 0 else ""
    return f"{sign}{growth:.0%}"


def _delta_str(week_delta: float) -> str:
    """Format week_delta as a signed display string, e.g. '↑ +7.2' or '↓ −3.1'."""
    if week_delta >= 0:
        return f"↑ +{week_delta:.1f}"
    return f"↓ {week_delta:.1f}"


def _delta_color(week_delta: float, accent: str) -> str:
    """Return accent color for positive delta, red for negative."""
    return accent if week_delta >= 0 else "#ff6b6b"


def _build_entry(entry: RankingEntry) -> Dict[str, Union[str, float]]:
    """Convert a RankingEntry to a template-ready dict."""
    return {
        "keyword": entry["keyword"],
        "growth": entry["growth"],
        "pct_str": _pct_str(entry["growth"]),
        "bar_pct": _bar_pct(entry["growth"]),
    }


def _build_daily_entry(entry: DailyRankingEntry, accent: str) -> Dict[str, Union[str, float]]:
    """Convert a DailyRankingEntry to a template-ready dict for Card 2.

    Args:
        entry: DailyRankingEntry from AnalysisResult.
        accent: Current status accent color hex string.

    Returns:
        Dict with keyword, pct_str, delta_str, bar_pct, pct_color fields.
    """
    pct = entry["pct"]
    delta = entry["delta"]
    sign = "+" if pct >= 0 else ""
    pct_str = f"{sign}{pct:.0%}"
    delta_str = f"{'+' if delta >= 0 else ''}{int(delta)} 件"
    bar_pct = round(min(abs(pct) / 1.0, 1.0) * 100, 1)  # 100% fill at ±100% change
    pct_color = accent if pct >= 0 else "#ff6b6b"
    return {
        "keyword": entry["keyword"],
        "pct_str": pct_str,
        "delta_str": delta_str,
        "bar_pct": bar_pct,
        "pct_color": pct_color,
    }


def _split_rankings(result: AnalysisResult) -> tuple[list, list]:
    """Split rankings into drivers and cooling lists, capped at max sizes."""
    drivers: list = []
    cooling: list = []
    for entry in result["rankings"]:
        ctx_entry = _build_entry(entry)
        if entry["growth"] > 0.005:
            if len(drivers) < _MAX_DRIVERS:
                drivers.append(ctx_entry)
        else:
            if len(cooling) < _MAX_COOLING:
                cooling.append(ctx_entry)
    return drivers, cooling


def _base_context(result: AnalysisResult) -> dict:
    """Build shared context fields present in all card templates."""
    accent = STATUS_COLORS.get(result["status"], STATUS_COLORS["cold"])
    return {
        "date": result["date"],
        "status_raw": _STATUS_BADGE.get(result["status"], result["status"].upper()),
        "phase_label": _PHASE_LABELS.get(result["status"], result["status"].title()),
        "warming_up": result["warming_up"],
        "accent_color": accent,
        "author_handle": AUTHOR_HANDLE,
    }


def _build_context_index(result: AnalysisResult) -> dict:
    """Build Jinja2 context for card_index.html (Card 1)."""
    ctx = _base_context(result)
    accent = ctx["accent_color"]
    week_delta = result.get("week_delta", 0.0)
    ctx.update(
        {
            "index_int": int(result["index"]),
            "gauge_circumference": round(_GAUGE_CIRCUMFERENCE, 2),
            "arc_offset": _arc_offset(result["index"]),
            "delta_str": _delta_str(week_delta),
            "delta_color": _delta_color(week_delta, accent),
        }
    )
    return ctx


def _build_context_daily(result: AnalysisResult) -> dict:
    """Build Jinja2 context for card_drivers.html (Card 2 — daily signal)."""
    ctx = _base_context(result)
    accent = ctx["accent_color"]
    daily = result.get("daily_rankings", [])
    ctx["daily_rankings"] = [_build_daily_entry(e, accent) for e in daily[:_MAX_DAILY]]
    return ctx


def _build_context_weekly(result: AnalysisResult) -> dict:
    """Build Jinja2 context for card_cooling.html (Card 3 — weekly brief, two columns)."""
    ctx = _base_context(result)
    drivers, cooling = _split_rankings(result)
    ctx.update(
        {
            "drivers": drivers,
            "cooling": cooling,
            "driver_summary": _DRIVER_SUMMARIES.get(result["status"], ""),
            "cooling_summary": _COOLING_SUMMARIES.get(result["status"], ""),
        }
    )
    return ctx


# ---------------------------------------------------------------------------
# Async render core
# ---------------------------------------------------------------------------


async def _render_all_cards(
    templates: list[tuple[str, dict, Path]],
) -> None:
    """Render multiple HTML templates to PNGs in sequence using a single browser launch.

    Args:
        templates: List of (template_name, context_dict, output_png_path) tuples.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        for template_name, context, png_path in templates:
            page = await browser.new_page(
                viewport={"width": IMAGE_WIDTH, "height": IMAGE_HEIGHT},
            )
            await page.set_content(context["_html"], wait_until="domcontentloaded")
            await page.screenshot(
                path=str(png_path),
                clip={"x": 0, "y": 0, "width": IMAGE_WIDTH, "height": IMAGE_HEIGHT},
                type="png",
            )
            await page.close()
            logger.info("PNG saved: %s", png_path)
        await browser.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(
    result: AnalysisResult, output_dir: Union[Path, None] = None
) -> tuple[Path, Path, Path, Path]:
    """Render the three daily index cards and social post text.

    Renders card_index.html, card_drivers.html, and card_cooling.html via
    Jinja2, then screenshots each with Playwright Chromium to produce three
    1080×1080 PNGs.  Also writes a plain-text social post.

    Card assignments:
        Card 1 (card_index.html)   — core index gauge + week delta
        Card 2 (card_drivers.html) — today vs yesterday signal per keyword
        Card 3 (card_cooling.html) — weekly brief: rising (left) / cooling (right)

    Args:
        result: AnalysisResult from analyzer.py.
        output_dir: Override output directory (defaults to config.OUTPUT_DIR).

    Returns:
        Tuple of (index_png, daily_png, weekly_png, txt_path).
    """
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    date_slug = result["date"].replace("-", "_")
    index_png = out_dir / f"card1_index_{date_slug}.png"
    daily_png = out_dir / f"card2_daily_{date_slug}.png"
    weekly_png = out_dir / f"card3_weekly_{date_slug}.png"
    txt_path = out_dir / "post.txt"

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    def _render_template(tpl_name: str, context: dict) -> str:
        tpl = env.get_template(tpl_name)
        return tpl.render(**context)

    # Build HTML for each card
    cards: list[tuple[str, dict, Path]] = [
        ("card_index.html", _build_context_index(result), index_png),
        ("card_drivers.html", _build_context_daily(result), daily_png),
        ("card_cooling.html", _build_context_weekly(result), weekly_png),
    ]

    rendered: list[tuple[str, dict, Path]] = []
    for tpl_name, ctx, png_path in cards:
        html = _render_template(tpl_name, ctx)
        ctx["_html"] = html
        rendered.append((tpl_name, ctx, png_path))

    # Screenshot all cards in one browser session
    asyncio.run(_render_all_cards(rendered))

    # Write social post text
    _write_post(result, txt_path)

    return index_png, daily_png, weekly_png, txt_path


def _write_post(result: AnalysisResult, txt_path: Path) -> None:
    """Write a plain-text social media post to txt_path.

    Args:
        result: AnalysisResult dict.
        txt_path: Destination file path.
    """
    week_delta = result.get("week_delta", 0.0)
    delta_sign = "+" if week_delta >= 0 else ""
    delta_part = f"  {delta_sign}{week_delta:.1f} vs last week" if not result["warming_up"] else ""

    lines: list[str] = [
        f"AI Shovel Index  {result['date']}",
        "",
        f"Score   {int(result['index'])} / 100{delta_part}",
        f"Status  {result['status'].upper()}",
        "",
    ]

    drivers = [e for e in result["rankings"] if e["growth"] > 0.005][:_MAX_DRIVERS]
    cooling = [e for e in result["rankings"] if e["growth"] <= 0.005][:_MAX_COOLING]

    if drivers:
        lines.append("Rising")
        for entry in drivers:
            pct = entry["growth"]
            sign = "+" if pct >= 0 else ""
            lines.append(f"  {entry['keyword']}  {sign}{pct:.0%}")

    if cooling:
        lines.append("Cooling")
        for entry in cooling:
            pct = entry["growth"]
            sign = "+" if pct >= 0 else ""
            lines.append(f"  {entry['keyword']}  {sign}{pct:.0%}")

    if result["warming_up"]:
        lines += ["", "(warming up — fewer than 7 days of data)"]

    lines += ["", f"{AUTHOR_HANDLE}  #AIshovelindex #AI #tech"]

    txt_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("post.txt saved: %s", txt_path)
