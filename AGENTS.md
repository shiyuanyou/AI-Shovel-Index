# SYSTEM INSTRUCTIONS: AI AGENT WORKFLOW LOGIC

This file (`AGENTS.md`) is the core governor of the AI Agent's behavior in this repository.
You must read and adhere to these rules before taking any action.

## 1. Memory Architecture Framework

This project uses a Long-Term Memory (LTM) / Short-Term Memory (STM) separation protocol.

### 1.1 Long-Term Memory (LTM) — `docs/`
- `docs/vision.md`: Product goals, target audience, core value, immutable rules.
- `docs/architecture.md`: Tech stack, directory structure, architectural patterns, global conventions.

### 1.2 Short-Term Memory (STM) — `docs/`
- `docs/stm_current.md`: Active workspace — goals, task breakdowns, in-progress decisions, and
  `- [ ]` checklists for the **current** development version.

### 1.3 Memory Archive — `docs/archive/`
- Contains deprecated/completed STM files (e.g., `stm_v0.md`).
- **STRICT RULE**: Do NOT open or reference archive files unless the user explicitly asks.

## 2. Bootstrapping & Context Loading

On session start, follow this sequence in order:
1. Verify that `docs/vision.md`, `docs/architecture.md`, and `docs/stm_current.md` exist.
2. Silently ingest all three files.
3. Base all coding, planning, and debugging solely on the ingested active memory.

## 3. Workflow Modes

### 3.1 PLAN Mode (Architecture & Scoping)
Role: Tech Lead / System Architect. Do NOT write application code.
- Digest new PRD / User Requirements.
- Update `docs/architecture.md` if the tech stack, schema, or directory logic changes.
- Decompose the milestone into atomic `- [ ]` tasks in `docs/stm_current.md`.

### 3.2 BUILD Mode (Execution)
Role: Senior Developer.
- Every file and code change must align with `docs/architecture.md`.
- Execute only tasks listed in `docs/stm_current.md`.
- Immediately update `docs/stm_current.md` after each sub-task (flip `- [ ]` to `- [x]`).
- Never rewrite files outside the current STM scope without user permission.

## 4. Version Bump / Archiving Procedure

When the user says "v1 is done" or "bump" / "archive":
1. Briefly review the completed `docs/stm_current.md`.
2. Move it to `docs/archive/stm_current_v[N].md`.
3. Create a fresh blank `docs/stm_current.md`.
4. Ask the user for the PRD / goals of the next version.

## 5. Global Technical Standards

### 5.1 Backend
- Language: **Python 3.11+** (target). The local macOS dev machine runs system Python 3.9.6;
  always invoke via `python3` / `python3 -m pytest` / `python3 -m black`, etc. — never bare
  `python` or `pytest`.
- Framework: FastAPI (if a web layer is ever needed). Currently a pure pipeline, no server.

### 5.2 Frontend (if added later)
- Framework: Vue 3 + Vite.

## 6. Violation Constraints

- **UNAUTHORIZED BROWSING**: Do not browse the file system indiscriminately. Stick to files
  defined in `docs/architecture.md` and the active STM tasks.
- **SILENT DRIFT**: Do not alter core architecture without updating `docs/architecture.md` and
  gaining user consent first.

---

## 7. Build & Run Commands

> All commands must be run from the repo root. Use `python3` (not `python`) on macOS.

### Environment Setup
```bash
# Install Python dependencies
python3 -m pip install -r requirements.txt

# Install Playwright's Chromium browser (required for crawler AND HTML rendering)
python3 -m playwright install chromium
```

### Running the Pipeline
```bash
# Full daily pipeline (crawl → analyze → render → output)
python3 run_daily.py

# With date override (backfill / testing)
python3 run_daily.py --date 2026-03-06

# Dry-run: crawl one keyword without writing to DB
python3 crawler.py --keyword "AI 副业" --dry-run
```

### Testing
```bash
# Run all tests
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_analyzer.py -v

# Run a single test function
python3 -m pytest tests/test_analyzer.py::TestGetStatus::test_cold -v

# Run renderer tests (writes preview images to tests/fixtures/output/)
python3 -m pytest tests/test_renderer.py -v
```

### Lint & Format
```bash
# Format code (non-negotiable, line length 100)
python3 -m black . --line-length 100

# Check formatting without writing
python3 -m black . --line-length 100 --check

# Lint
python3 -m ruff check .

# Type checking
python3 -m mypy . --ignore-missing-imports
```

---

## 8. Code Style Guidelines

### Language & Version Target
- Target is Python 3.11+; the local dev machine runs 3.9.6 (Xcode system Python).
- Use `match` statements and `tomllib` only in code paths gated by a version check, or accept
  that CI (3.11+) may differ from local.
- **Union syntax**: Use `Union[X, Y]` from `typing` (not `X | Y`) to stay compatible with 3.9.
  The `X | Y` syntax requires Python 3.10+.

### Type Annotations
- All public function signatures MUST have full type annotations (parameters + return type).
- Use `TypedDict` for structured dicts passed between modules. All shared TypedDicts live in
  `config.py`.
- Never use `Any` unless unavoidable; add a `# noqa: ANN401` comment with justification.
- Pillow type stubs are incomplete; use `# type: ignore[arg-type]` with a short comment where
  needed (e.g., `Image.new("RGB", size, color)  # type: ignore[arg-type]`).

### Imports
Order enforced by `ruff` (isort-compatible):
1. Standard library (`os`, `sqlite3`, `datetime`, `pathlib`, …)
2. Third-party (`playwright`, `PIL`, `pytest`, `jinja2`, …)
3. Local modules (`config`, `analyzer`, `renderer`, …)

One blank line between groups. No wildcard imports (`from x import *`).

### Naming Conventions
| Construct           | Convention        | Example                    |
|---------------------|-------------------|----------------------------|
| Variables/functions | `snake_case`      | `avg_price`, `fetch_kw()`  |
| Module-level constants | `UPPER_SNAKE_CASE` | `DB_PATH`, `INDEX_WEIGHTS` |
| Classes             | `PascalCase`      | `RenderConfig`             |
| Files / modules     | `snake_case`      | `analyzer.py`              |
| Private helpers     | `_snake_case`     | `_load_font()`, `_hex()`   |

### Formatting
- Max line length: **100 characters** (`black --line-length 100`).
- Strings: prefer double quotes (black default).
- No trailing commas required but black will add them — do not fight it.

### Error Handling
- **Never** use bare `except:`. Always catch a specific exception class.
- Every caught exception must be logged with `logging.error(...)` before re-raising or
  failing gracefully.
- Crawler failures write `item_count=0` to DB (preserving date continuity). Never skip a
  date silently.

### Logging
- Use the standard `logging` module everywhere. No `print()` in production code paths
  (only in `--dry-run` or `if __name__ == "__main__"` debug blocks).
- Format: `%(asctime)s [%(levelname)s] %(module)s — %(message)s`
- Levels: `INFO` for normal flow, `WARNING` for degraded/cold-start, `ERROR` for failures.

### Docstrings
- Every module must have a top-level one-liner docstring (+ blank line + details if needed).
- Every public function must have a docstring describing: purpose, args, and return value.
- Style: plain prose — not Google/NumPy style. Keep it minimal and accurate.

---

## 9. Project-Specific Conventions

### Data Contract Between Modules
Modules communicate exclusively via plain `dict` objects typed with `TypedDict` from `config.py`.
No shared global state between modules.

**DB Row (written by `crawler.py`):**
```python
class CrawlRecord(TypedDict):
    date: str           # "YYYY-MM-DD"
    keyword: str
    item_count: int     # 0 on crawl failure
    seller_count: int
    avg_price: float
```

**Analysis Result (output of `analyzer.py`, input to `renderer.py`):**
```python
class AnalysisResult(TypedDict):
    date: str           # "YYYY-MM-DD"
    index: float        # 0.0–100.0
    status: str         # "cold" | "early" | "rising" | "speculation" | "bubble"
    rankings: list[RankingEntry]  # sorted descending by growth
    warming_up: bool    # True when DB has fewer than HISTORY_DAYS (7) days of data
```

### Date Handling
- All dates are `"YYYY-MM-DD"` strings. Never pass `datetime` objects between modules.
- Generate today's date with `datetime.date.today().isoformat()`.

### Output Paths
- Read all output paths from `config.py` constants (`OUTPUT_DIR`, `DB_PATH`).
- Never hardcode paths inside module code.
- Output directory: `output/`; DB: `data/index.db` (both excluded from git via `.gitignore`).

### Renderer — HTML + Playwright Screenshot (current approach)
- `renderer.py` renders `templates/card.html` via Jinja2, then screenshots with Playwright.
- This is preferred over direct Pillow drawing because: Playwright is already a dependency,
  HTML/CSS handles CJK fonts natively via system font stack, and layout is easier to maintain.
- Jinja2 (`jinja2>=3.1.0`) is a required dependency — add to `requirements.txt` if missing.
- Keep `render(result, output_dir?)` signature stable; tests depend on it.

### Cold Start
- When DB contains fewer than 7 days of data, `analyzer.py` uses the available days' mean.
- `warming_up: True` is passed to `renderer.py`, which adds a "(warming up)" label to both
  the image and `post.txt`.

### Crawler Resilience
- On any crawl failure for a keyword, log the error and write a zero-record to DB.
- Do NOT abort the full run when one keyword fails; process all keywords and report all
  failures at the end of the run.

### Testing Conventions
- Use in-memory SQLite (not `data/index.db`) for all `test_analyzer.py` tests.
- Tests that generate image/text output write to `tests/fixtures/output/` (git-ignored PNGs).
- Group related tests in `class Test<Feature>` blocks for clarity.
- Test functions are plain `def` (synchronous); async tests require `@pytest.mark.asyncio`.
