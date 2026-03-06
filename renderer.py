"""renderer.py — Render AnalysisResult into a 1080×1080 PNG and post.txt.

Visual style: Stripe / Linear-inspired dark gradient theme via HTML + Playwright screenshot.
    - Near-black background (#0d0d0d) with subtle radial glow
    - Status-driven accent colour
    - Square layout (1080×1080) optimised for social media feeds
    - Top: brand header + date + status pill
    - Middle: large SVG semicircle gauge showing the index score
    - Bottom: keyword ranking rows (drivers above, cooling below)
    - Footer: tagline + yoyoo.ai domain

CSS is compiled via Tailwind CLI (npm run build:css) and inlined at render time so
Playwright's set_content() works without a base URL (no <link href> external file).

Dependencies: jinja2, playwright, Pillow (test-time verification only)
"""

import asyncio
import logging
import math
from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

from config import (
    AnalysisResult,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    OUTPUT_DIR,
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

# Max entries shown per column
_MAX_PER_COL = 4

# SVG gauge geometry
# Semi-circle: radius 220, stroke-width 24
# Arc length of a full semicircle = π * r
_GAUGE_RADIUS: int = 220
_GAUGE_CIRCUMFERENCE: float = math.pi * _GAUGE_RADIUS  # ≈ 691.2


def _arc_offset(index: float) -> float:
    """Compute SVG stroke-dashoffset for the gauge arc fill.

    The arc uses stroke-dasharray = circumference.  When dashoffset equals
    circumference the arc is empty; when 0 it is full.  We interpolate
    linearly between those extremes based on the 0–100 index value.

    Args:
        index: Index score in [0, 100].

    Returns:
        stroke-dashoffset value (float, rounded to 2 dp).
    """
    fraction = max(0.0, min(float(index), 100.0)) / 100.0
    return round(_GAUGE_CIRCUMFERENCE * (1.0 - fraction), 2)


def _bar_pct(growth: float) -> float:
    """Convert a growth ratio to a bar fill percentage in [0, 100].

    For positive: maps 0 → 0%, +2.0 → 100%.
    For negative: maps 0 → 0%, -1.0 → 100% (absolute value, shown red).
    """
    return round(min(abs(growth) / 2.0, 1.0) * 100, 1)


def _pct_str(growth: float) -> str:
    """Format growth ratio as a signed percentage string, e.g. '+52%' or '-10%'."""
    sign = "+" if growth >= 0 else ""
    return f"{sign}{growth:.0%}"


def _build_context(result: AnalysisResult) -> dict:
    """Build the Jinja2 template rendering context from an AnalysisResult.

    Splits rankings into two lists: drivers (growth > 0.005) and cooling
    (growth ≤ 0.005), each capped at _MAX_PER_COL entries.  Also computes
    the SVG gauge arc offset.

    Args:
        result: AnalysisResult dict from analyzer.py.

    Returns:
        Dict suitable for Jinja2 template rendering.
    """
    accent = STATUS_COLORS.get(result["status"], STATUS_COLORS["cold"])

    drivers = []
    cooling = []
    for entry in result["rankings"]:
        ctx_entry = {
            "keyword": entry["keyword"],
            "growth": entry["growth"],
            "pct_str": _pct_str(entry["growth"]),
            "bar_pct": _bar_pct(entry["growth"]),
        }
        if entry["growth"] > 0.005:
            if len(drivers) < _MAX_PER_COL:
                drivers.append(ctx_entry)
        else:
            if len(cooling) < _MAX_PER_COL:
                cooling.append(ctx_entry)

    return {
        "date": result["date"],
        "index_int": int(result["index"]),
        "status_raw": result["status"].upper(),
        "phase_label": _PHASE_LABELS.get(result["status"], result["status"].title()),
        "warming_up": result["warming_up"],
        "accent_color": accent,
        "drivers": drivers,
        "cooling": cooling,
        # SVG gauge
        "gauge_circumference": round(_GAUGE_CIRCUMFERENCE, 2),
        "arc_offset": _arc_offset(result["index"]),
    }


# ---------------------------------------------------------------------------
# Async render core
# ---------------------------------------------------------------------------


async def _render_html_to_png(html_content: str, png_path: Path) -> None:
    """Screenshot an HTML string to a PNG file using Playwright Chromium.

    The viewport is fixed to IMAGE_WIDTH × IMAGE_HEIGHT; the screenshot is
    clipped to exactly that size to guarantee a 1080×1080 RGB output.

    CSS is already inlined into html_content so no external file loading is
    needed — set_content() works reliably in offline/CI environments.

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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(
    result: AnalysisResult, output_dir: Union[Path, None] = None
) -> tuple[Path, Path]:
    """Render the daily index card and social post text.

    Renders templates/card.html via Jinja2, inlines the compiled Tailwind CSS
    from templates/card.compiled.css, then screenshots with Playwright Chromium
    to produce a 1080×1080 PNG. Also writes a plain-text social post.

    Args:
        result: AnalysisResult from analyzer.py.
        output_dir: Override output directory (defaults to config.OUTPUT_DIR).

    Returns:
        Tuple of (png_path, txt_path).
    """
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    date_slug = result["date"].replace("-", "_")
    png_path = out_dir / f"index_{date_slug}.png"
    txt_path = out_dir / "post.txt"

    # Load compiled CSS and inline it so Playwright set_content() works offline
    compiled_css_path = TEMPLATES_DIR / "card.compiled.css"
    css_content = compiled_css_path.read_text(encoding="utf-8")

    # Render HTML template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("card.html")
    context = _build_context(result)
    context["inlined_css"] = css_content
    html_content = template.render(**context)

    # Screenshot via Playwright (sync wrapper around async)
    asyncio.run(_render_html_to_png(html_content, png_path))

    # Write social post text
    _write_post(result, txt_path)

    return png_path, txt_path


def _write_post(result: AnalysisResult, txt_path: Path) -> None:
    """Write a plain-text social media post to txt_path.

    Args:
        result: AnalysisResult dict.
        txt_path: Destination file path.
    """
    lines: list[str] = [
        f"AI Shovel Index  {result['date']}",
        "",
        f"Score   {int(result['index'])} / 100",
        f"Status  {result['status'].upper()}",
        "",
    ]

    if result["rankings"]:
        lines.append("Keywords")
        for entry in result["rankings"][:5]:
            pct = entry["growth"]
            sign = "+" if pct >= 0 else ""
            lines.append(f"  {entry['keyword']}  {sign}{pct:.0%}")

    if result["warming_up"]:
        lines += ["", "(warming up — fewer than 7 days of data)"]

    lines += ["", "#AIshovelindex #AI #tech"]

    txt_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("post.txt saved: %s", txt_path)
