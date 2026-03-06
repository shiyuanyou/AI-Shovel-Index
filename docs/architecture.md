# AI Shovel Index — Architecture

## Current Goal

This project produces a daily, shareable sentiment snapshot for the "AI shovel selling" market by crawling Xianyu, calculating an index, and rendering image cards plus a post caption.

The current product shape is still intentionally small:
- no web app
- no realtime API
- no external database
- one scheduled batch pipeline per day

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | Local `.venv` and CI should match |
| Crawl | Playwright async | Chromium-based browser crawl for Xianyu |
| Storage | SQLite `data/index.db` | Single local DB file |
| Analysis | Python stdlib | Pure calculation layer |
| Rendering | Jinja2 + Playwright screenshot | Inline HTML/CSS rendered to PNG |
| Automation | GitHub Actions now | Cloud cron or server scheduler is the next target |
| Quality | pytest + black + ruff + mypy | Required before shipping changes |

## Current Directory Layout

```text
AI-Shovel-Index/
├── AGENTS.md
├── analyzer.py
├── config.py
├── crawler.py
├── preview_all.py
├── renderer.py
├── run_daily.py
├── requirements.txt
├── package.json
├── data/
│   └── index.db
├── docs/
│   ├── architecture.md
│   ├── stm_current.md
│   └── vision.md
├── templates/
│   ├── card_index.html
│   ├── card_drivers.html
│   ├── card_cooling.html
│   ├── card_weekly.html
│   ├── card.html
│   ├── card.css
│   └── card.compiled.css
├── tests/
│   ├── test_analyzer.py
│   ├── test_renderer.py
│   └── fixtures/
└── .github/
  └── workflows/
    └── daily.yml
```

## Actual Data Flow

```text
Xianyu search result pages
  ↓ crawler.py
SQLite crawl_records
  ↓ analyzer.py
AnalysisResult
  ↓ renderer.py
output/card1_index_YYYY_MM_DD.png
output/card2_daily_YYYY_MM_DD.png
output/card3_weekly_YYYY_MM_DD.png
output/post.txt
```

Modules communicate through `TypedDict` objects defined in `config.py`.

## Module Responsibilities

### `config.py`
- centralizes paths, constants, and render settings
- defines shared `TypedDict` contracts
- initializes the SQLite schema

### `crawler.py`
- crawls Xianyu per keyword with Playwright
- writes one `CrawlRecord` per keyword per date
- writes zero-value fallback rows when a keyword crawl fails

### `analyzer.py`
- reads recent records from SQLite
- computes the overall `index`, `status`, `rankings`, `daily_rankings`, `warming_up`, and `week_delta`
- exposes the `analyze(target_date)` entry point

### `renderer.py`
- builds three card contexts from `AnalysisResult`
- renders Jinja2 templates to HTML
- screenshots them with Playwright Chromium
- writes the social caption to `post.txt`

### `run_daily.py`
- orchestrates crawl -> save -> analyze -> render
- is the main batch entry point for local runs and CI

## Shared Data Contracts

### `CrawlRecord`
```python
class CrawlRecord(TypedDict):
  date: str
  keyword: str
  item_count: int
  seller_count: int
  avg_price: float
```

### `RankingEntry`
```python
class RankingEntry(TypedDict):
  keyword: str
  growth: float
```

### `DailyRankingEntry`
```python
class DailyRankingEntry(TypedDict):
  keyword: str
  delta: float
  pct: float
```

### `AnalysisResult`
```python
class AnalysisResult(TypedDict):
  date: str
  index: float
  status: str
  rankings: list[RankingEntry]
  daily_rankings: list[DailyRankingEntry]
  warming_up: bool
  week_delta: float
```

## Database Schema

```sql
CREATE TABLE crawl_records (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  date         TEXT NOT NULL,
  keyword      TEXT NOT NULL,
  item_count   INTEGER NOT NULL,
  seller_count INTEGER NOT NULL,
  avg_price    REAL NOT NULL,
  created_at   TEXT DEFAULT (datetime('now')),
  UNIQUE(date, keyword)
);
```

## Render Output

Current output is three 1080x1080 PNG cards plus one text file.

| Output | Template | Purpose |
|---|---|---|
| Card 1 | `templates/card_index.html` | Core index gauge and week delta |
| Card 2 | `templates/card_drivers.html` | Today vs yesterday per-keyword signal |
| Card 3 | `templates/card_cooling.html` | Weekly brief with rising and cooling columns |
| Text | generated in `renderer.py` | Caption for social posting |

Legacy files kept but not used by the active renderer:
- `templates/card_weekly.html`
- `templates/card.html`
- `templates/card.css`
- `templates/card.compiled.css`

## Operational Conventions

- Dates move between modules as `YYYY-MM-DD` strings.
- All paths should come from `config.py`.
- Renderer UI text in HTML templates should remain Chinese.
- `run_daily.py` is the source of truth for the batch pipeline.
- Tests should avoid touching the production DB.

## Current Deployment Shape

The project is production-like in workflow, but not yet fully deployment-hardened.

### Working Today
- GitHub Actions can schedule daily runs.
- Playwright-based crawl and render are already integrated.
- SQLite history is preserved in-repo through committed `data/index.db`.

### Known Deployment Gaps
- timezone handling is still local-date based in runtime code
- SQLite concurrency safeguards are minimal
- render failure validation is thin
- CI still contains a legacy Node/Tailwind step that is no longer needed for active templates
- font consistency on Linux servers is not guaranteed yet

## Deployment Refactor Direction

Before moving from GitHub Actions to a cloud server, prefer this sequence:
1. make date handling explicit and timezone-safe
2. simplify CI to the active renderer path only
3. harden SQLite usage for single-run scheduling
4. validate renderer outputs and fail clearly
5. document server prerequisites for Playwright, fonts, and writable storage

These tasks are tracked in `docs/stm_current.md`.
