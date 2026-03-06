# AI-Shovel-Index Agent Guide

Use this file as the workspace-wide instruction source for this repo.

## Session Bootstrap

Read these files before making changes:
1. `docs/vision.md`
2. `docs/architecture.md`
3. `docs/stm_current.md`

Do not open `docs/archive/` unless the user explicitly asks.

## Workflow Modes

### PLAN Mode
- Act as a tech lead.
- Do not write application code.
- Update `docs/architecture.md` if the actual structure or deployment model changes.
- Break new work into atomic `- [ ]` tasks in `docs/stm_current.md`.

### BUILD Mode
- Act as a senior developer.
- Only implement tasks already listed in `docs/stm_current.md`.
- Flip `- [ ]` to `- [x]` immediately after finishing each sub-task.
- Do not rewrite files outside the active STM scope without user approval.

### Version Bump
When the user says `done`, `bump`, or `archive`:
1. Move `docs/stm_current.md` to `docs/archive/stm_current_v[N].md`.
2. Create a fresh `docs/stm_current.md`.
3. Ask for the next version goals.

## Build And Test

Run commands from repo root. Use `.venv/bin/python3`; never use bare `python`, `python3`, or `pytest`.

### Environment Setup
```bash
/opt/homebrew/Caskroom/miniconda/base/envs/py312/bin/python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

On Linux cloud hosts without the local conda path, use:
```bash
python3.12 -m venv .venv
```

### Main Commands
```bash
.venv/bin/python3 run_daily.py
.venv/bin/python3 run_daily.py --date 2026-03-06
.venv/bin/python3 crawler.py --keyword "AI 副业" --dry-run
.venv/bin/python3 preview_all.py
.venv/bin/python3 -m pytest tests/ -v
.venv/bin/python3 -m black . --line-length 100 --check
.venv/bin/python3 -m ruff check .
.venv/bin/python3 -m mypy . --ignore-missing-imports
```

`npm ci` and `npm run build:css` are legacy-only tasks for `templates/card.html`. The active 3-card renderer uses inline CSS and does not need Node during normal development.

## Architecture Snapshot

- Pipeline: `crawler.py -> SQLite -> analyzer.py -> renderer.py -> 3 PNGs + post.txt`
- Shared contracts live in `config.py` as `TypedDict`s.
- Active templates:
  - `templates/card_index.html`
  - `templates/card_drivers.html`
  - `templates/card_cooling.html`
- Legacy templates kept for reference only:
  - `templates/card_weekly.html`
  - `templates/card.html`
- Current render output:
  - `card1_index_YYYY_MM_DD.png`
  - `card2_daily_YYYY_MM_DD.png`
  - `card3_weekly_YYYY_MM_DD.png`
  - `post.txt`

## Project Conventions

- Target runtime is Python 3.12.
- Public function signatures should be fully typed.
- Keep imports grouped as stdlib, third-party, local.
- Use `config.py` constants for paths, author handle, and shared settings.
- User-facing HTML template text must remain Chinese.
- Do not hardcode brand strings or output paths outside `config.py`.
- Prefer `logging`; `print()` is only acceptable in CLI or dry-run output.
- If you change data structures such as `AnalysisResult`, update all affected tests and fixtures in the same task.

## Deployment Notes

- `renderer.py` and `crawler.py` require Playwright Chromium and Linux system dependencies on servers.
- Treat SQLite as a single-writer local store unless the user explicitly changes the storage architecture.
- Cloud deployment work should verify timezone handling, writable `data/` and `output/`, and Chinese font availability for screenshots.
- If architecture or deployment assumptions change, update `docs/architecture.md` before or with the code change.

