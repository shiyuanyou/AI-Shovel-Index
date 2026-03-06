"""renderer.py — Render AnalysisResult into a 1200×630 PNG and post.txt.

Visual style: Apple Keynote-inspired dark theme rendered via HTML + Playwright screenshot.
    - Pure black background (#000000)
    - Status-driven accent colour
    - Left panel: score hero + status pill
    - Right panel: keyword growth rankings with bar chart

Dependencies: jinja2, playwright, Pillow (test-time verification only)
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

from config import (
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
# Template context helpers
# ---------------------------------------------------------------------------

_MAX_RANKINGS = 6  # number of keyword rows shown on the card


def _bar_pct(growth: float) -> float:
    """Convert a growth ratio to a bar fill percentage in [0, 100].

    Maps growth of -1.0 → 0%, 0.0 → 33%, +2.0 → 100%.
    """
    normalised = (growth + 1.0) / 3.0
    return round(max(0.0, min(1.0, normalised)) * 100, 1)


def _pct_str(growth: float) -> str:
    """Format growth ratio as a signed percentage string, e.g. '+52%' or '-10%'."""
    sign = "+" if growth >= 0 else ""
    return f"{sign}{growth:.0%}"


def _build_context(result: AnalysisResult) -> dict:
    """Build the Jinja2 template rendering context from an AnalysisResult.

    Args:
        result: AnalysisResult dict from analyzer.py.

    Returns:
        Dict suitable for Jinja2 template rendering.
    """
    accent = STATUS_COLORS.get(result["status"], STATUS_COLORS["cold"])

    rankings_ctx = []
    for entry in result["rankings"][:_MAX_RANKINGS]:
        rankings_ctx.append(
            {
                "keyword": entry["keyword"],
                "growth": entry["growth"],
                "pct_str": _pct_str(entry["growth"]),
                "bar_pct": _bar_pct(entry["growth"]),
            }
        )

    return {
        "date": result["date"],
        "index_int": int(result["index"]),
        "status": result["status"].upper(),
        "warming_up": result["warming_up"],
        "accent_color": accent,
        "rankings": rankings_ctx,
    }


# ---------------------------------------------------------------------------
# Async render core
# ---------------------------------------------------------------------------


async def _render_html_to_png(html_content: str, png_path: Path) -> None:
    """Screenshot an HTML string to a PNG file using Playwright Chromium.

    The viewport is fixed to IMAGE_WIDTH × IMAGE_HEIGHT; the screenshot is
    clipped to exactly that size to guarantee a 1200×630 RGB output.

    Args:
        html_content: Full HTML document as a string.
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

    Renders templates/card.html via Jinja2, then screenshots it with Playwright
    Chromium to produce a 1200×630 PNG. Also writes a plain-text social post.

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

    # Render HTML template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("card.html")
    context = _build_context(result)
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
