# SYSTEM INSTRUCTIONS: AI AGENT WORKFLOW LOGIC

This file (`AGENTS.md`) is the core governor of the AI Agent's behavior in this repository.
You must read and adhere to these rules before taking any action.

## 1. Memory Architecture Framework

This project utilizes a Long-Term Memory (LTM) and Short-Term Memory (STM) separation protocol
to maintain context efficiency and prevent token pollution.

### 1.1 Long-Term Memory (LTM)
Located in `docs/`:
- `docs/vision.md`: Contains the ultimate product goals, target audience, core user value, and immutable foundational rules.
- `docs/architecture.md`: Contains the current technology stack, directory structure, core architectural patterns, and global coding conventions.

### 1.2 Short-Term Memory (STM)
Located in `docs/`:
- `docs/stm_current.md`: The active workspace document. It contains the exact goals, task breakdowns, in-progress decisions, and to-do lists for the *current* development version (e.g., v0, v1, v2.5).

### 1.3 Memory Archive
Located in `docs/archive/`:
- Contains deprecated/completed STM files (e.g., `stm_v0.md`).
- STRICT RULE: Do not open, read, or reference any files in the `archive/` directory unless the user explicitly commands you to retrieve historical data.

## 2. Bootstrapping & Context Loading

Upon session start or mode switch, follow strictly this initialization sequence:
1. Verify the existence of the Memory Architecture (`docs/vision.md`, `docs/architecture.md`, `docs/stm_current.md`). Provide a brief status summary if they do not exist.
2. Silently ingest the contents of LTM and STM files.
3. Base all subsequent coding, planning, and debugging solely on the ingested active memory.

## 3. Workflow Modes

### 3.1 PLAN Mode Guidelines (Architecture & Scoping)
When operating in Planning/Architecting mode:
- Your role is Tech Lead and System Architect.
- Do not write operational application code.
- Focus on digesting new User Requirements (e.g., `PRD.md` provided by the user).
- Update `docs/architecture.md` immediately if the new plan requires modifying the tech stack, data schemas, or directory logic.
- Draft or modify `docs/stm_current.md` to break down the new milestone into atomic, verifiable tasks using markdown checkboxes (`- [ ]`).

### 3.2 BUILD Mode Guidelines (Execution)
When operating in Building/Coding mode:
- Your role is Senior Developer.
- Strict Alignment: Every file structure change and code logic must align with `docs/architecture.md`.
- Task Execution: Check `docs/stm_current.md` for pending tasks. Execute them precisely.
- State Synchronization: Whenever a sub-task is completed, or a critical localized design decision is made during coding, you must update `docs/stm_current.md` (e.g., change `- [ ]` to `- [x]`, add short notes).
- Never randomly rewrite files outside the scope of the current STM without user permission.

## 4. Iteration and Archiving Procedure (Version Bump)

When the user announces the completion of a version (e.g., "v1 is done, let's move to v2") or commands a "bump" / "archive", execute the following Standard Operating Procedure (SOP) sequentially:

1. Review and Summarize: Briefly review the completed `docs/stm_current.md`.
2. Move to Archive: Rename `docs/stm_current.md` to `stm_current_v[VERSION_NUMBER].md` and move it to `docs/archive/`.
3. Reset: Create a fresh, blank `docs/stm_current.md`.
4. Await Input: Prompt the user to provide the PRD or general goals for the upcoming version to begin the new PLAN Mode.

## 5. Global Technical Standards

Unless explicitly overridden by the user in a specific PRD, adhere to the following:

### 5.1 Frontend Development
- Framework: Vue 3 + Vite (default for any frontend work).

### 5.2 Backend Development
- Language: Python 3.11+.
- Framework: FastAPI (if a web API layer is needed).
- This project is currently a pure Python pipeline with no web server.

## 6. Violation Constraints

- UNAUTHORIZED BROWSING: Do not browse the file system indiscriminately. Stick to files defined in the architecture and active STM tasks.
- SILENT DRIFT: Do not alter the core architecture without first proposing the change in `docs/architecture.md` and gaining user consent.

---

## 7. Build & Run Commands

### Environment Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser (required for crawler)
playwright install chromium
```

### Running the Pipeline
```bash
# Run the full daily pipeline (crawl → analyze → render → output)
python run_daily.py

# Run with a specific date override (for backfill/testing)
python run_daily.py --date 2026-03-06

# Dry-run: crawl a single keyword without writing to DB
python crawler.py --keyword "AI 副业" --dry-run
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_analyzer.py -v

# Run a single test function
pytest tests/test_analyzer.py::test_cold_start_index -v

# Run renderer tests (generates output to tests/fixtures/output/)
pytest tests/test_renderer.py -v
```

### Lint & Format
```bash
# Format code
black . --line-length 100

# Type checking
mypy . --ignore-missing-imports

# Lint
ruff check .
```

---

## 8. Code Style Guidelines

### Language & Version
- Python 3.11+ exclusively. Use `match` statements, `tomllib`, and modern typing where appropriate.

### Type Annotations
- All function signatures MUST have full type annotations (parameters + return type).
- Use `TypedDict` for structured dicts passed between modules (defined in `config.py`).
- Never use `Any` unless absolutely unavoidable; add a `# noqa` comment with justification.

### Imports
Order (enforced by `ruff`):
1. Standard library (`os`, `sqlite3`, `datetime`, etc.)
2. Third-party (`playwright`, `pillow`, `pytest`, etc.)
3. Local modules (`config`, `analyzer`, etc.)

Blank line between each group. No wildcard imports (`from x import *`).

### Naming Conventions
| Construct | Convention | Example |
|-----------|-----------|---------|
| Variables / functions | `snake_case` | `avg_price`, `fetch_keyword()` |
| Constants | `UPPER_SNAKE_CASE` | `DB_PATH`, `INDEX_WEIGHTS` |
| Classes | `PascalCase` (minimize use) | `RenderConfig` |
| Files / modules | `snake_case` | `analyzer.py` |

### Formatting
- Max line length: **100 characters**.
- Use `black` as the auto-formatter (non-negotiable).
- Strings: prefer double quotes (black default).

### Error Handling
- Never use bare `except:`. Always catch specific exceptions.
- All caught exceptions MUST be logged with `logging.error(...)` before re-raising or failing gracefully.
- Crawler failures write `item_count=0` to DB (preserving date continuity) — never skip a date silently.

### Logging
- Use the standard `logging` module. No `print()` in production code (only in `--dry-run` or debug paths).
- Format: `%(asctime)s [%(levelname)s] %(module)s — %(message)s`
- Level: `INFO` for normal flow, `WARNING` for degraded operation, `ERROR` for failures.

### Docstrings
- Every module must have a top-level module docstring (one-liner + blank line + detail if needed).
- Every public function must have a docstring describing purpose, args, and return value.
- Use plain prose, not Google/NumPy style (keep it minimal).

---

## 9. Project-Specific Conventions

### Data Contract Between Modules
Modules communicate exclusively via plain `dict` objects (typed with `TypedDict`). No shared global state.

**DB Row (written by `crawler.py`):**
```python
class CrawlRecord(TypedDict):
    date: str          # "YYYY-MM-DD"
    keyword: str
    item_count: int
    seller_count: int
    avg_price: float
```

**Analysis Result (output of `analyzer.py`, input to `renderer.py`):**
```python
class AnalysisResult(TypedDict):
    date: str          # "YYYY-MM-DD"
    index: float       # 0.0–100.0
    status: str        # "cold" | "early" | "rising" | "speculation" | "bubble"
    rankings: list[dict]  # [{"keyword": str, "growth": float}, ...]
    warming_up: bool   # True if fewer than 7 days of data exist
```

### Date Handling
- All dates are passed as `"YYYY-MM-DD"` strings. Never pass `datetime` objects between modules.
- Use `datetime.date.today().isoformat()` to generate today's date string.

### Output Paths
- All output paths are read from `config.py`. Never hardcode paths in module code.
- Output directory: `output/`; DB path: `data/index.db`.

### Cold Start
- When DB contains fewer than 7 days of data, `analyzer.py` uses the available days' mean.
- The `warming_up: True` flag is passed to `renderer.py`, which adds a subtle "(warming up)" label to the image.

### Crawler Resilience
- On any crawl failure for a keyword, log the error and write a zero-record to DB.
- Do not abort the full run if one keyword fails; process all keywords and report failures at end.
