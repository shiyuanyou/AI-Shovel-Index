# AGENTS.md — AI Agent Instructions for AI-Shovel-Index

Read this file before taking any action. It governs all agent behavior in this repo.

---

## 1. Session Bootstrap (always do this first)

1. Read `docs/vision.md` — product goals and immutable rules.
2. Read `docs/architecture.md` — tech stack, directory layout, architectural patterns.
3. Read `docs/stm_current.md` — active task list and in-progress decisions.
4. Base all work on these three files. **Do NOT open `docs/archive/`** unless the user explicitly asks.

---

## 2. Workflow Modes

### PLAN Mode
Role: Tech Lead. Do NOT write application code.
- Digest new requirements; update `docs/architecture.md` if the stack or structure changes.
- Decompose work into atomic `- [ ]` tasks in `docs/stm_current.md`.

### BUILD Mode
Role: Senior Developer.
- Only execute tasks listed in `docs/stm_current.md`.
- Flip `- [ ]` → `- [x]` in `docs/stm_current.md` immediately after each sub-task.
- Never rewrite files outside the current STM scope without explicit user permission.

### Version Bump
When user says "done", "bump", or "archive":
1. Move `docs/stm_current.md` → `docs/archive/stm_current_v[N].md`.
2. Create a fresh `docs/stm_current.md`.
3. Ask for the next version's goals.

---

## 3. Build & Run Commands

> All commands run from repo root. Use `.venv/bin/python3` — never bare `python`, `python3`, or `pytest`.
> The project uses a local `.venv` (Python 3.12) to ensure consistent behaviour across local editors, terminals, and CI.

### Environment Setup
```bash
# 1. Create project-local virtual environment (one-time, Python 3.12)
/opt/homebrew/Caskroom/miniconda/base/envs/py312/bin/python3 -m venv .venv

# 2. Install Python dependencies
.venv/bin/pip install -r requirements.txt

# 3. Install Playwright Chromium browser
.venv/bin/playwright install chromium

# Activate once per shell session (optional, shortens commands)
source .venv/bin/activate
```

> **Note for cloud/CI**: on a fresh Linux host without conda, replace step 1 with:
> `python3.12 -m venv .venv` (ensure Python 3.12 is installed first).
>
> **Node / Tailwind**: `npm ci` + `npm run build:css` are only needed if editing the legacy
> `templates/card.html`. The active 4-card templates (`card_index.html` etc.) use pure inline
> CSS and do **not** require a Node build step.

### Pipeline
```bash
.venv/bin/python3 run_daily.py                      # full run: crawl → analyze → render
.venv/bin/python3 run_daily.py --date 2026-03-06    # backfill a specific date
.venv/bin/python3 crawler.py --keyword "AI 副业" --dry-run  # test crawl, no DB write
.venv/bin/python3 preview_all.py                    # render all 4 cards × 5 scenarios to tests/fixtures/preview/
```

### Testing
```bash
# All tests
.venv/bin/python3 -m pytest tests/ -v

# Single file
.venv/bin/python3 -m pytest tests/test_analyzer.py -v

# Single test function
.venv/bin/python3 -m pytest tests/test_analyzer.py::TestGetStatus::test_cold -v

# Renderer tests (outputs PNGs to tests/fixtures/output/)
.venv/bin/python3 -m pytest tests/test_renderer.py -v
```

### Lint & Format (run before every commit)
```bash
.venv/bin/python3 -m black . --line-length 100          # format (non-negotiable)
.venv/bin/python3 -m black . --line-length 100 --check  # CI-style check
.venv/bin/python3 -m ruff check .                        # lint
.venv/bin/python3 -m ruff check . --fix                  # auto-fix lint errors
.venv/bin/python3 -m mypy . --ignore-missing-imports     # type check
```

---

## 4. Code Style

### Language & Compatibility
- **Target**: Python 3.12 (local `.venv` and CI both use 3.12).
- `X | Y` union syntax and `match` statements are fine — both require 3.10+, which 3.12 satisfies.
- Prefer modern syntax (`list[str]`, `dict[str, int]`, `X | Y`) over legacy `List`/`Dict`/`Union`.

### Type Annotations
- All public function signatures **must** have full annotations (params + return type).
- All inter-module data structures are `TypedDict`s defined in `config.py`. Use them — never pass raw dicts.
- Never use `Any` unless unavoidable; add `# noqa: ANN401` with a justification comment.
- Annotate local variables when mypy cannot infer the type (e.g., list/dict literals that hold mixed types).

### Imports
Enforced by `ruff` (isort-compatible); three groups separated by one blank line:
1. Standard library
2. Third-party (`playwright`, `jinja2`, `PIL`, `pytest`, …)
3. Local modules (`config`, `analyzer`, `renderer`, …)

No wildcard imports (`from x import *`).

### Naming
| Construct | Convention | Example |
|---|---|---|
| Variables / functions | `snake_case` | `avg_price`, `fetch_kw()` |
| Module-level constants | `UPPER_SNAKE_CASE` | `DB_PATH`, `INDEX_WEIGHTS` |
| Classes / TypedDicts | `PascalCase` | `AnalysisResult`, `RenderConfig` |
| Files / modules | `snake_case` | `analyzer.py` |
| Private helpers | `_snake_case` | `_arc_offset()`, `_hex()` |

### Formatting
- Max line length: **100** (`black --line-length 100`).
- Double quotes (black default). Do not fight black's trailing-comma decisions.

### Error Handling
- **Never** use bare `except:`. Always catch a specific exception class.
- Log every caught exception with `logging.error(...)` before re-raising or failing gracefully.
- Crawler: on any per-keyword failure, write `item_count=0` to DB and continue. Never abort the full run.

### Logging
- Standard `logging` module only. No `print()` in production paths.
- Allowed `print()` locations: `--dry-run` branches and `if __name__ == "__main__"` blocks.
- Format: `%(asctime)s [%(levelname)s] %(module)s — %(message)s`
- Levels: `INFO` normal flow · `WARNING` degraded/cold-start · `ERROR` failures.

### Docstrings
- Every module: top-level one-liner (+ blank line + details if needed).
- Every public function: purpose, args, return value — plain prose, not Google/NumPy style.

---

## 5. Project Conventions

### Data Flow
```
crawler.py  →  DB (CrawlRecord)  →  analyzer.py  →  AnalysisResult  →  renderer.py  →  4× PNG + post.txt
```
Modules communicate **only** via `TypedDict` dicts. No shared global state. All TypedDicts live in `config.py`.

### Key Types (see `config.py` for canonical definitions)
- `CrawlRecord` — one DB row per keyword per date; `item_count=0` signals a crawl failure.
- `RankingEntry` — `{keyword, growth}` where `growth` is ratio vs 7-day baseline; 1.0 = flat.
- `AnalysisResult` — `{date, index, status, rankings, warming_up, week_delta}`.
  - `week_delta: float` — today's index minus oldest-day index in the 7-day window; `0.0` when `warming_up=True`.

### Dates
- Always `"YYYY-MM-DD"` strings. Never pass `datetime` objects between modules.
- Generate with `datetime.date.today().isoformat()`.

### Paths
- Read all paths from `config.py` constants (`OUTPUT_DIR`, `DB_PATH`, `TEMPLATES_DIR`).
- Never hardcode paths inside module logic.

### Renderer
- `renderer.py` renders 4 Jinja2 HTML templates via Playwright Chromium headless screenshot.
- Templates use **pure inline CSS** — no external stylesheets, no `<link href>` tags.
  (Playwright `set_content()` has no base URL; external links would 404.)
- `render(result, output_dir?) -> tuple[Path, Path, Path, Path, Path]` — 4 PNGs + `post.txt`.
- Output filenames: `card1_index_YYYY_MM_DD.png`, `card2_drivers_…`, `card3_cooling_…`, `card4_weekly_…`.
- Image size: **1080×1080** px (social media 1:1 square).
- Keep `render()` signature stable; tests depend on it.
- Card text is in **Chinese** (中文). Do not add English UI strings to templates.
- `AUTHOR_HANDLE = "@yoyoostone"` — defined in `config.py`; always read from there, never hardcode.

### Templates (4 active cards + 1 legacy)
| File | Card | Content |
|------|------|---------|
| `card_index.html` | 1 | 指数仪表盘、大数字、week_delta、@yoyoostone |
| `card_drivers.html` | 2 | 热门驱动 — Top 4 上升关键词 + 进度条 |
| `card_cooling.html` | 3 | 退热信号 — 下降关键词，红色强调 |
| `card_weekly.html` | 4 | 本周简报 — 快速上升 / 降温中 叙述摘要 |
| `card.html` | — | 已废弃，保留备用，renderer 不再引用 |

### Cold Start
- Fewer than 7 days in DB → `warming_up=True` in `AnalysisResult`, `week_delta=0.0`.
- Renderer shows "数据积累中 — 不足 7 天" label instead of delta.

### Testing Conventions
- `test_analyzer.py`: use in-memory SQLite, never touch `data/index.db`.
- `test_renderer.py`: outputs to `tests/fixtures/output/` (git-ignored).
- Group tests in `class Test<Feature>` blocks.
- Sync tests: plain `def`. Async tests: `@pytest.mark.asyncio`.
- When adding a field to `AnalysisResult`, update **all** test fixtures that construct it.

---

## 6. Constraints

- **No unauthorized browsing**: only open files referenced in `docs/architecture.md` or the active STM task list.
- **No silent drift**: never change architecture without updating `docs/architecture.md` and getting user consent.
- **No bare `python`/`pytest`**: always `.venv/bin/python3` / `.venv/bin/python3 -m pytest`.
- **No English UI text in templates**: all user-visible strings in HTML templates must be Chinese.
- **No hardcoded paths or brand strings**: use `config.py` constants (`OUTPUT_DIR`, `AUTHOR_HANDLE`, etc.).

