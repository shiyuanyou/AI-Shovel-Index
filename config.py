"""config.py — Global constants, TypedDicts, and DB initialization.

Centralizes all configuration so other modules never hardcode paths,
keywords, or weights. Also owns the DB schema and init routine.
"""

import sqlite3
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR: Path = Path(__file__).parent
DATA_DIR: Path = ROOT_DIR / "data"
OUTPUT_DIR: Path = ROOT_DIR / "output"
TEMPLATES_DIR: Path = ROOT_DIR / "templates"
DB_PATH: Path = DATA_DIR / "index.db"

# ---------------------------------------------------------------------------
# Keywords to crawl
# ---------------------------------------------------------------------------

KEYWORDS: list[str] = [
    "ChatGPT 教程",
    "ChatGPT 副业",
    "AI 副业",
    "Sora 教程",
    "Stable Diffusion 教程",
    "Midjourney 教程",
    "Claude 教程",
    "AI 变现",
]

# ---------------------------------------------------------------------------
# Index calculation weights
# ---------------------------------------------------------------------------

WEIGHT_ITEMS: float = 0.6
WEIGHT_SELLERS: float = 0.4
INDEX_SCALE: float = 50.0
INDEX_MAX: float = 100.0
HISTORY_DAYS: int = 7  # days of history used for baseline average

# ---------------------------------------------------------------------------
# Status thresholds  (lower bound inclusive)
# ---------------------------------------------------------------------------

STATUS_THRESHOLDS: list[tuple[float, str]] = [
    (80.0, "bubble"),
    (60.0, "speculation"),
    (40.0, "rising"),
    (20.0, "early"),
    (0.0, "cold"),
]

# ---------------------------------------------------------------------------
# Render style constants
# ---------------------------------------------------------------------------

IMAGE_WIDTH: int = 1080
IMAGE_HEIGHT: int = 1080
BG_COLOR: str = "#0a0a0a"
TEXT_COLOR: str = "#ffffff"
SUBTEXT_COLOR: str = "#888888"
AUTHOR_HANDLE: str = "@yoyoostone"

STATUS_COLORS: dict[str, str] = {
    "cold": "#4a9eff",
    "early": "#a8e6cf",
    "rising": "#ffd93d",
    "speculation": "#ff6b35",
    "bubble": "#ff2d55",
}

# ---------------------------------------------------------------------------
# TypedDicts — shared data contracts between modules
# ---------------------------------------------------------------------------


class CrawlRecord(TypedDict):
    """One row written to DB by crawler.py for a single keyword on a single date."""

    date: str  # "YYYY-MM-DD"
    keyword: str
    item_count: int  # 0 if crawl failed
    seller_count: int
    avg_price: float


class RankingEntry(TypedDict):
    """Per-keyword growth entry inside AnalysisResult."""

    keyword: str
    growth: float  # ratio vs 7-day baseline; 1.0 = flat


class AnalysisResult(TypedDict):
    """Output of analyzer.py, consumed by renderer.py."""

    date: str  # "YYYY-MM-DD"
    index: float  # 0.0–100.0
    status: str  # "cold" | "early" | "rising" | "speculation" | "bubble"
    rankings: list[RankingEntry]  # sorted descending by growth
    warming_up: bool  # True when DB has fewer than HISTORY_DAYS days of data
    week_delta: float  # index change vs 7 days ago (positive = rising, negative = falling)


# ---------------------------------------------------------------------------
# DB initialization
# ---------------------------------------------------------------------------

DB_SCHEMA: str = """
CREATE TABLE IF NOT EXISTS crawl_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    keyword      TEXT NOT NULL,
    item_count   INTEGER NOT NULL,
    seller_count INTEGER NOT NULL,
    avg_price    REAL NOT NULL,
    created_at   TEXT DEFAULT (datetime('now')),
    UNIQUE(date, keyword)
);
"""


def init_db() -> None:
    """Create the data directory and initialise the SQLite schema if needed.

    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(DB_SCHEMA)
        conn.commit()


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to sqlite3.Row.

    Callers are responsible for closing the connection (use as context manager).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
