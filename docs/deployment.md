# AI Shovel Index — Deployment Guide

## Recommended First Target

For the current architecture, the safest first deployment target is a single Linux server running one scheduled batch job.

Decision: the first supported deployment target is `Ubuntu VPS + systemd timer`.
Cron remains acceptable for simple setups, but systemd is the preferred default because it gives clearer ownership, restart behavior, and logs.

Recommended order of simplicity:
1. Ubuntu VPS + cron or systemd timer
2. Docker container on a single VPS
3. Managed cloud runtime only after timezone, storage, and Playwright dependencies are fully hardened

Why this is the best first step:
- SQLite is currently a local single-file store
- Playwright needs Chromium and Linux system libraries
- the app is a daily batch job, not a request/response web service

## Runtime Requirements

- Python 3.12
- project-local `.venv`
- Playwright Chromium browser
- Linux system libraries required by Playwright
- writable `data/` and `output/` directories
- Chinese-capable fonts available to Chromium

## Server Setup

Run from repo root.

### 1. Create the virtual environment
```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Install Playwright browser
```bash
.venv/bin/playwright install chromium
```

### 3. Install Linux dependencies for Playwright
On Ubuntu, the simplest option is:
```bash
.venv/bin/python3 -m playwright install-deps chromium
```

If that command is not available in the target image, install the equivalent system packages manually before the first run.

### 4. Verify directories and permissions
Make sure these paths are writable by the deployment user:
- `data/`
- `output/`

## Font Expectations

The templates contain Chinese text and currently rely on system font fallback.

Before production deployment, verify that rendered screenshots display Chinese correctly on the server. If not, install a CJK font package such as Noto Sans CJK and rerun the preview or daily pipeline.

## Daily Run Commands

### Full run
```bash
.venv/bin/python3 run_daily.py
```

### Backfill a specific date
```bash
.venv/bin/python3 run_daily.py --date 2026-03-06
```

### Deployment smoke test
```bash
.venv/bin/python3 smoke_test.py
```

Use this on a fresh server before the first scheduled run. It skips crawling and
verifies that Python, Playwright Chromium, templates, and writable output paths
can still produce all three cards plus `post.txt`.

### Crawl dry run
```bash
.venv/bin/python3 crawler.py --keyword "AI 副业" --dry-run
```

### Tests and checks
```bash
.venv/bin/python3 -m pytest tests/ -v
.venv/bin/python3 -m black . --line-length 100 --check
.venv/bin/python3 -m ruff check .
.venv/bin/python3 -m mypy . --ignore-missing-imports
```

## Runtime Diagnostics

The batch entry point now emits a few intentionally stable log lines for cloud troubleshooting:
- `RUN_CONTEXT` shows the target date for the current batch
- `CRAWL_SUMMARY` reports keyword count, total items, failed keyword count, and failure ratio
- `CRAWL_HEALTH` escalates to warning or error when zero-item keywords cross configured thresholds
- `ANALYSIS_SUMMARY` records index, status, warming-up state, and weekly delta
- `OUTPUT_SUMMARY` records the final output file paths

If many keywords suddenly fall back to zero records, check the `CRAWL_HEALTH` line first before trusting the day's index.

## Suggested Deployment Flow

### Option A: VPS + cron
Use a single scheduled command:
```bash
cd /path/to/AI-Shovel-Index && .venv/bin/python3 run_daily.py >> logs/daily.log 2>&1
```

Example cron for 10:00 Beijing time on a UTC server:
```cron
0 2 * * * cd /path/to/AI-Shovel-Index && .venv/bin/python3 run_daily.py >> logs/daily.log 2>&1
```

### Option B: systemd timer
Prefer this if you want better logs, restart behavior, and clearer service ownership than cron.

Repo-ready assets are now available for this path:
- `deploy/vps/README.md`
- `deploy/vps/bootstrap_ubuntu.sh`
- `deploy/systemd/ai-shovel-index.service`
- `deploy/systemd/ai-shovel-index.timer`

Recommended flow:
1. run `deploy/vps/bootstrap_ubuntu.sh` on the server
2. install the systemd unit templates from `deploy/systemd/`
3. run one manual `smoke_test.py` and one manual `run_daily.py`
4. enable `ai-shovel-index.timer`

## Persistence Decision

For cloud deployment, `data/index.db` should move to server-local persistence and stop being treated as a git-synchronized artifact.

Use this rule going forward:
- GitHub Actions may continue committing `data/index.db` while it remains the temporary hosted scheduler
- VPS or other cloud server deployments should keep `data/index.db` on local disk or attached persistent storage
- do not rely on git push/pull as the primary persistence mechanism once the batch runs on a server

Why this is the chosen direction:
- SQLite is designed for local single-writer storage
- server-local persistence avoids mixing runtime state with source-control history
- it removes an unnecessary dependency on git credentials during batch execution
- it fits the current single-host deployment model better than DB-in-repo synchronization

## Pre-Deploy Checklist

- [ ] `docs/architecture.md` matches the real pipeline
- [ ] server has Python 3.12
- [ ] `.venv` created and dependencies installed
- [ ] Playwright Chromium installed successfully
- [ ] Linux dependencies installed successfully
- [ ] Chinese fonts render correctly in screenshots
- [ ] `.venv/bin/python3 smoke_test.py` succeeds
- [ ] `data/` and `output/` are writable
- [ ] one manual `run_daily.py` execution succeeds
- [ ] output PNGs and `post.txt` look correct on the server

## Current Known Gaps

These are not blockers for local testing, but should be addressed before long-term unattended deployment:
- SQLite still relies on a single-writer deployment assumption even though journal mode is now pinned to `DELETE`
- overlapping scheduled runs are still not explicitly locked yet

## GitHub Actions Notes

The current `daily.yml` workflow now matches the repo conventions more closely:
- it creates a project-local `.venv`
- it installs Python dependencies into that `.venv`
- it installs Playwright with `.venv/bin/python3` and `.venv/bin/playwright`
- manual dispatch can choose `pipeline` or `smoke` mode for quick server verification
- runtime logs now surface crawl degradation in stdout instead of only listing zero-value keywords
- its `data/index.db` commit step should be treated as a transition path, not the long-term cloud persistence model

## What Not To Deploy Yet

The project is not yet shaped like a web app or API service. Avoid deploying it as:
- a long-running HTTP server
- a multi-instance autoscaling service
- a shared multi-writer database workload

The current architecture is best treated as a scheduled batch renderer.