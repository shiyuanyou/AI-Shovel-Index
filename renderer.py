"""renderer.py — Render AnalysisResult into a 1200×630 PNG and post.txt.

Visual style: Apple Keynote-inspired dark theme.
    - Near-black background (#0a0a0a)
    - Pure white primary text
    - Status-driven accent colour
    - Minimal layout: score hero left, trend bar right, keyword rankings bottom

Dependencies: Pillow (PIL)
"""

import logging
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont, ImageFont as BitmapFont

FontType = Union[FreeTypeFont, BitmapFont]

from config import (
    AnalysisResult,
    BG_COLOR,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    OUTPUT_DIR,
    STATUS_COLORS,
    SUBTEXT_COLOR,
    TEXT_COLOR,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


def _hex(color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' string to (r, g, b) tuple."""
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex_a(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = _hex(color)
    return r, g, b, alpha


# ---------------------------------------------------------------------------
# Font loading — graceful fallback chain
# ---------------------------------------------------------------------------

# Font candidates are tried in order; first existing file wins.
# Chinese glyphs require a CJK-capable font — STHeiti / Arial Unicode on macOS,
# Noto CJK on Linux CI.  Helvetica/DejaVu are kept as ASCII-only last resorts.
_FONT_CANDIDATES = [
    # macOS — CJK-capable (covers all Chinese keyword characters)
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    # macOS — ASCII fallback
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    # Linux (GitHub Actions Ubuntu) — CJK
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    # Linux — ASCII fallback
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

_FONT_CANDIDATES_BOLD = [
    # macOS — CJK-capable
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    # macOS — ASCII fallback
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    # Linux — CJK
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    # Linux — ASCII fallback
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int, bold: bool = False) -> FontType:
    """Load a TrueType font at the given size; fall back to PIL default if unavailable."""
    candidates = _FONT_CANDIDATES_BOLD if bold else _FONT_CANDIDATES
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    logger.warning("No TrueType font found; falling back to PIL default bitmap font.")
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------


def _draw_text_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: FontType,
    color: str,
    x_start: int = 0,
    x_end: int = IMAGE_WIDTH,
) -> None:
    """Draw text horizontally centred within [x_start, x_end]."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = x_start + (x_end - x_start - tw) // 2
    draw.text((x, y), text, font=font, fill=_hex(color))


def _draw_growth_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    growth: float,
    accent: tuple[int, int, int],
    bar_height: int = 6,
) -> None:
    """Draw a horizontal progress bar representing keyword growth ratio.

    growth is clamped to [-1, +3] for display; 0 = flat, positive = above baseline.
    """
    # Normalise: treat 0 growth as 50% bar width, +2 as 100%, negative as < 50%
    normalised = max(0.0, min(1.0, (growth + 1.0) / 3.0))
    filled = int(width * normalised)

    # Track
    draw.rounded_rectangle(
        [x, y, x + width, y + bar_height],
        radius=bar_height // 2,
        fill=(*_hex(SUBTEXT_COLOR), 80),
    )
    if filled > 0:
        draw.rounded_rectangle(
            [x, y, x + filled, y + bar_height],
            radius=bar_height // 2,
            fill=(*accent, 255),
        )


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------


def render(
    result: AnalysisResult, output_dir: Union[Path, None] = None
) -> tuple[Path, Path]:
    """Render the daily index card and social post text.

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

    accent_hex = STATUS_COLORS.get(result["status"], STATUS_COLORS["cold"])
    accent_rgb = _hex(accent_hex)

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------
    img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), _hex(BG_COLOR))  # type: ignore[arg-type]
    draw = ImageDraw.Draw(img, "RGBA")

    # Subtle grid lines for visual depth
    for gx in range(0, IMAGE_WIDTH, 80):
        draw.line([(gx, 0), (gx, IMAGE_HEIGHT)], fill=(*_hex("#1a1a1a"), 255), width=1)
    for gy in range(0, IMAGE_HEIGHT, 80):
        draw.line([(0, gy), (IMAGE_WIDTH, gy)], fill=(*_hex("#1a1a1a"), 255), width=1)

    # ------------------------------------------------------------------
    # Layout constants
    # ------------------------------------------------------------------
    PAD = 64
    DIVIDER_X = IMAGE_WIDTH // 2  # vertical divider between hero and chart area

    # ------------------------------------------------------------------
    # Left panel — Score hero
    # ------------------------------------------------------------------

    # Eyebrow label
    font_eyebrow = _load_font(16)
    draw.text(
        (PAD, PAD), "AI SHOVEL INDEX", font=font_eyebrow, fill=_hex(SUBTEXT_COLOR)
    )

    # Date
    font_date = _load_font(14)
    draw.text((PAD, PAD + 28), result["date"], font=font_date, fill=_hex(SUBTEXT_COLOR))

    # Giant score
    font_score_big = _load_font(120, bold=True)
    score_str = str(int(result["index"]))
    draw.text((PAD, 100), score_str, font=font_score_big, fill=_hex(TEXT_COLOR))

    # "/100" in accent colour, smaller
    font_denom = _load_font(36, bold=True)
    score_bbox = draw.textbbox((PAD, 100), score_str, font=font_score_big)
    score_width = score_bbox[2] - score_bbox[0]
    draw.text(
        (PAD + score_width + 8, 185),
        "/ 100",
        font=font_denom,
        fill=accent_rgb,
    )

    # Status pill
    font_status = _load_font(22, bold=True)
    status_text = result["status"].upper()
    status_bbox = draw.textbbox((0, 0), status_text, font=font_status)
    pill_w = (status_bbox[2] - status_bbox[0]) + 32
    pill_h = 38
    pill_x = PAD
    pill_y = 280
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=pill_h // 2,
        fill=(*accent_rgb, 40),
        outline=(*accent_rgb, 180),
        width=1,
    )
    draw.text(
        (pill_x + 16, pill_y + 8),
        status_text,
        font=font_status,
        fill=accent_rgb,
    )

    # Warming-up notice
    if result["warming_up"]:
        font_wu = _load_font(13)
        draw.text(
            (PAD, pill_y + pill_h + 14),
            "warming up — fewer than 7 days of data",
            font=font_wu,
            fill=_hex(SUBTEXT_COLOR),
        )

    # ------------------------------------------------------------------
    # Vertical divider
    # ------------------------------------------------------------------
    draw.line(
        [(DIVIDER_X, PAD), (DIVIDER_X, IMAGE_HEIGHT - PAD)],
        fill=(*_hex("#2a2a2a"), 255),
        width=1,
    )

    # ------------------------------------------------------------------
    # Right panel — Keyword rankings
    # ------------------------------------------------------------------
    RIGHT_PAD = DIVIDER_X + PAD
    font_section = _load_font(13)
    draw.text(
        (RIGHT_PAD, PAD), "KEYWORD GROWTH", font=font_section, fill=_hex(SUBTEXT_COLOR)
    )

    font_kw = _load_font(17, bold=True)
    font_pct = _load_font(17)
    bar_width = IMAGE_WIDTH - RIGHT_PAD - PAD - 70  # leave space for % label

    top_rankings = result["rankings"][:6]
    row_y = PAD + 36
    row_gap = 62

    for entry in top_rankings:
        kw = entry["keyword"]
        growth = entry["growth"]  # ratio delta; 0.0 = flat, 0.5 = +50%
        pct_str = f"{growth:+.0%}"

        # Keyword name (truncate if too long)
        kw_display = kw if len(kw) <= 14 else kw[:13] + "…"
        draw.text((RIGHT_PAD, row_y), kw_display, font=font_kw, fill=_hex(TEXT_COLOR))

        # Percentage — colour: green if positive, muted if flat/negative
        pct_color = (
            accent_hex
            if growth > 0.01
            else (SUBTEXT_COLOR if growth >= -0.01 else "#ff453a")
        )
        draw.text(
            (IMAGE_WIDTH - PAD - 55, row_y),
            pct_str,
            font=font_pct,
            fill=_hex(pct_color),
        )

        # Growth bar
        _draw_growth_bar(
            draw,
            x=RIGHT_PAD,
            y=row_y + 26,
            width=bar_width,
            growth=growth,
            accent=accent_rgb,
        )

        row_y += row_gap

    # ------------------------------------------------------------------
    # Bottom tagline
    # ------------------------------------------------------------------
    font_tag = _load_font(13)
    tagline = "Tracking AI speculation cycles via second-hand marketplace data"
    _draw_text_centered(draw, tagline, IMAGE_HEIGHT - PAD + 10, font_tag, SUBTEXT_COLOR)

    # ------------------------------------------------------------------
    # Save PNG
    # ------------------------------------------------------------------
    img.save(png_path, "PNG", optimize=True)
    logger.info("PNG saved: %s", png_path)

    # ------------------------------------------------------------------
    # post.txt — social media copy
    # ------------------------------------------------------------------
    _write_post(result, txt_path)

    return png_path, txt_path


def _write_post(result: AnalysisResult, txt_path: Path) -> None:
    """Write a plain-text social media post to txt_path."""
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
