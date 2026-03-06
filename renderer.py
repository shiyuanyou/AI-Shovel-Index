"""renderer.py — Render AnalysisResult into four 1080×1080 PNGs and post.txt.

Card layout (all 1:1 square, optimised for social media):
    Card 1 — card_index.html   : core index gauge with week delta
    Card 2 — card_drivers.html : top 4 rising keywords
    Card 3 — card_cooling.html : cooling keywords
    Card 4 — card_weekly.html  : weekly brief narrative summary

CSS is inlined directly in each HTML template; no external Tailwind compilation
is needed for the new cards.  The legacy card.html and card.compiled.css remain
in the templates directory but are no longer referenced by this module.

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
    "cold": "Market Quiet",
    "early": "Early Signal",
    "rising": "Rising Phase",
    "speculation": "Speculation Phase",
    "bubble": "Bubble Warning",
}

# Descriptions appended to the weekly brief (Card 4) per keyword category
_DRIVER_SUMMARIES: dict[str, str] = {
    "cold": "Speculative activity remains subdued.",
    "early": "Early tutorial demand emerging — watch closely.",
    "rising": "Tutorial market heating up across multiple categories.",
    "speculation": "Strong speculative demand signals across AI niches.",
    "bubble": "Extreme tutorial proliferation — potential bubble territory.",
}

_COOLING_SUMMARIES: dict[str, str] = {
    "cold": "",
    "early": "",
    "rising": "Some topics losing momentum as new niches attract attention.",
    "speculation": "Rotation visible — capital chasing newer keywords.",
    "bubble": "Early signs of saturation in legacy AI tutorial categories.",
}

# Max drivers shown on Cards 2 & 4
_MAX_DRIVERS = 4
# Max cooling shown on Cards 3 & 4
_MAX_COOLING = 4

# SVG gauge geometry — Card 1
# Semi-circle: radius 240, path M 300 480 A 240 240 0 0 1 780 480
# Arc length = π × 240 ≈ 753.98
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
    """Build shared context fields present in all 4 card templates."""
    accent = STATUS_COLORS.get(result["status"], STATUS_COLORS["cold"])
    return {
        "date": result["date"],
        "status_raw": result["status"].upper(),
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


def _build_context_drivers(result: AnalysisResult) -> dict:
    """Build Jinja2 context for card_drivers.html (Card 2)."""
    ctx = _base_context(result)
    drivers, _ = _split_rankings(result)
    ctx["drivers"] = drivers
    return ctx


def _build_context_cooling(result: AnalysisResult) -> dict:
    """Build Jinja2 context for card_cooling.html (Card 3)."""
    ctx = _base_context(result)
    _, cooling = _split_rankings(result)
    ctx["cooling"] = cooling
    return ctx


def _build_context_weekly(result: AnalysisResult) -> dict:
    """Build Jinja2 context for card_weekly.html (Card 4)."""
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


async def _render_html_to_png(html_content: str, png_path: Path) -> None:
    """Screenshot an HTML string to a PNG file using Playwright Chromium.

    The viewport is fixed to IMAGE_WIDTH × IMAGE_HEIGHT; the screenshot is
    clipped to exactly that size to guarantee a 1080×1080 output.

    Args:
        html_content: Full HTML document as a string (CSS inlined).
        png_path: Destination path for the PNG file.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": IMAGE_WIDTH, "height": IMAGE_HEIGHT},
        )
        await page.set_content(html_content, wait_until="domcontentloaded")
        await page.screenshot(
            path=str(png_path),
            clip={"x": 0, "y": 0, "width": IMAGE_WIDTH, "height": IMAGE_HEIGHT},
            type="png",
        )
        await browser.close()
    logger.info("PNG saved: %s", png_path)


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
) -> tuple[Path, Path, Path, Path, Path]:
    """Render the four daily index cards and social post text.

    Renders card_index.html, card_drivers.html, card_cooling.html, and
    card_weekly.html via Jinja2, then screenshots each with Playwright Chromium
    to produce four 1080×1080 PNGs.  Also writes a plain-text social post.

    Args:
        result: AnalysisResult from analyzer.py.
        output_dir: Override output directory (defaults to config.OUTPUT_DIR).

    Returns:
        Tuple of (index_png, drivers_png, cooling_png, weekly_png, txt_path).
    """
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    date_slug = result["date"].replace("-", "_")
    index_png = out_dir / f"card1_index_{date_slug}.png"
    drivers_png = out_dir / f"card2_drivers_{date_slug}.png"
    cooling_png = out_dir / f"card3_cooling_{date_slug}.png"
    weekly_png = out_dir / f"card4_weekly_{date_slug}.png"
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
        ("card_drivers.html", _build_context_drivers(result), drivers_png),
        ("card_cooling.html", _build_context_cooling(result), cooling_png),
        ("card_weekly.html", _build_context_weekly(result), weekly_png),
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

    return index_png, drivers_png, cooling_png, weekly_png, txt_path


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
