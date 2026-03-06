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
| Automation | GitHub Actions, systemd, or Docker-hosted batch | CI uses project-local `.venv`; VPS can run native or Dockerized batch jobs |
| Quality | pytest + black + ruff + mypy | Required before shipping changes |

## Current Directory Layout

```text
AI-Shovel-Index/
├── AGENTS.md
├── .dockerignore
├── Dockerfile
├── analyzer.py
├── config.py
├── crawler.py
├── deploy/
│   ├── docker/
│   ├── systemd/
│   └── vps/
├── preview_all.py
├── renderer.py
├── smoke_test.py
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
- emits crawl health, analysis summary, and output summary logs for cloud troubleshooting

### `smoke_test.py`
- renders a fixed sample `AnalysisResult` without crawling live data
- verifies that Playwright Chromium and output writing work in a deployment environment
- is intended for first-run server checks and optional CI smoke execution

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
- Runtime defaults now use UTC date strings for scheduled batch execution.
- Renderer now validates required templates and expected output files before returning success.
- The workflow now installs dependencies into a project-local `.venv` and supports a manual smoke-test mode.
- `run_daily.py` now logs crawl health ratios and structured step summaries to stdout for easier cloud diagnosis.
- a repo-local VPS deployment kit now exists under `deploy/vps/` and `deploy/systemd/`
- a repo-local Docker deployment kit now exists under `Dockerfile`, `.dockerignore`, and `deploy/docker/`

### Known Deployment Gaps
- font consistency on Linux servers is not guaranteed yet
- SQLite still assumes a single-writer batch deployment even though journal mode is now forced to `DELETE`
- overlapping scheduled runs still need explicit protection on server deployments

## Deployment Decisions

- first deployment target: Ubuntu VPS with a systemd timer
- persistence strategy: use server-local `data/index.db` for cloud deployment; keep git-backed DB commits only as a transitional GitHub Actions behavior
- optimized upgrade path: run the batch inside a Docker image while keeping scheduling on the VPS host via systemd

## Deployment Refactor Direction

Before moving from GitHub Actions to a cloud server, prefer this sequence:
1. simplify CI to the active renderer path only
2. remove git-backed DB persistence once the server scheduler becomes the primary runtime
3. add explicit single-run protection if the deployment scheduler can overlap jobs
4. document server prerequisites for Playwright, fonts, and writable storage

These tasks are tracked in `docs/stm_current.md`.
