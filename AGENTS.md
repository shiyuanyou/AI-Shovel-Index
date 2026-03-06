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

> All commands run from repo root. Use `python3` — never bare `python` or `pytest`.
> `black`/`ruff`/`mypy` binaries live in `~/Library/Python/3.9/bin/`; invoke via `python3 -m <tool>` or full path if not on PATH.

### Environment Setup
```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium   # required for crawler AND renderer
npm ci                                    # install Tailwind CLI
npm run build:css                         # compile templates/card.compiled.css
```

### Pipeline
```bash
python3 run_daily.py                      # full run: crawl → analyze → render
python3 run_daily.py --date 2026-03-06   # backfill a specific date
python3 crawler.py --keyword "AI 副业" --dry-run  # test crawl, no DB write
```

### Testing
```bash
# All tests
python3 -m pytest tests/ -v

# Single file
python3 -m pytest tests/test_analyzer.py -v

# Single test function
python3 -m pytest tests/test_analyzer.py::TestGetStatus::test_cold -v

# Renderer tests (outputs PNGs to tests/fixtures/output/)
python3 -m pytest tests/test_renderer.py -v
```

### Lint & Format (run before every commit)
```bash
python3 -m black . --line-length 100          # format (non-negotiable)
python3 -m black . --line-length 100 --check  # CI-style check
python3 -m ruff check .                        # lint
python3 -m ruff check . --fix                  # auto-fix lint errors
python3 -m mypy . --ignore-missing-imports     # type check
```

---

## 4. Code Style

### Language & Compatibility
- **Target**: Python 3.11+. **Local dev**: Python 3.9.6 (Xcode system Python).
- Use `Union[X, Y]` from `typing` — never `X | Y` (requires 3.10+).
- Use `List[...]`, `Dict[...]`, `Tuple[...]` from `typing` for the same reason.
- `match` statements and `tomllib` are 3.10+/3.11+ — avoid unless gated by a version check.

### Type Annotations
- All public function signatures **must** have full annotations (params + return type).
- All inter-module data structures are `TypedDict`s defined in `config.py`. Use them.
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
crawler.py  →  DB (CrawlRecord)  →  analyzer.py  →  AnalysisResult  →  renderer.py  →  PNG + post.txt
```
Modules communicate **only** via `TypedDict` dicts. No shared global state. All TypedDicts live in `config.py`.

### Key Types (see `config.py` for the canonical definitions)
- `CrawlRecord` — one DB row per keyword per date; `item_count=0` signals a crawl failure.
- `RankingEntry` — `{keyword, growth}` where `growth` is ratio vs 7-day baseline.
- `AnalysisResult` — `{date, index, status, rankings, warming_up}`.

### Dates
- Always `"YYYY-MM-DD"` strings. Never pass `datetime` objects between modules.
- Generate with `datetime.date.today().isoformat()`.

### Paths
- Read all paths from `config.py` constants (`OUTPUT_DIR`, `DB_PATH`, `TEMPLATES_DIR`).
- Never hardcode paths inside module logic.

### Renderer
- `renderer.py` renders `templates/card.html` via Jinja2, screenshots with Playwright Chromium.
- CSS is **compiled** by Tailwind CLI (`npm run build:css` → `templates/card.compiled.css`) and **inlined** at render time into a `<style>` tag — never linked via `<link href>` (Playwright `set_content()` has no base URL).
- Keep `render(result, output_dir?)` signature stable; tests depend on it.
- Image size: **1080×1080** px.

### Cold Start
- Fewer than 7 days in DB → `warming_up=True` in `AnalysisResult`.
- Renderer adds a "(warming up)" label to image and `post.txt`.

### Testing Conventions
- `test_analyzer.py`: use in-memory SQLite, never touch `data/index.db`.
- `test_renderer.py`: outputs to `tests/fixtures/output/` (git-ignored).
- Group tests in `class Test<Feature>` blocks.
- Sync tests: plain `def`. Async tests: `@pytest.mark.asyncio`.

---

## 6. Constraints

- **No unauthorized browsing**: only open files referenced in `docs/architecture.md` or the active STM task list.
- **No silent drift**: never change architecture without updating `docs/architecture.md` and getting user consent.
- **No bare `python`/`pytest`**: always `python3` / `python3 -m pytest`.
