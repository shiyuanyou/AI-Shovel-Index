# AI Shovel Index — Deployment Guide

## Recommended First Target

For the current architecture, the safest first deployment target is a single Linux server running one scheduled batch job.

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

## Pre-Deploy Checklist

- [ ] `docs/architecture.md` matches the real pipeline
- [ ] server has Python 3.12
- [ ] `.venv` created and dependencies installed
- [ ] Playwright Chromium installed successfully
- [ ] Linux dependencies installed successfully
- [ ] Chinese fonts render correctly in screenshots
- [ ] `data/` and `output/` are writable
- [ ] one manual `run_daily.py` execution succeeds
- [ ] output PNGs and `post.txt` look correct on the server

## Current Known Gaps

These are not blockers for local testing, but should be addressed before long-term unattended deployment:
- runtime date handling is still based on local machine date
- SQLite concurrency protections are still minimal
- renderer does not yet validate all expected outputs before returning
- CI still contains a legacy Node/Tailwind step unrelated to the active 3-card renderer

## What Not To Deploy Yet

The project is not yet shaped like a web app or API service. Avoid deploying it as:
- a long-running HTTP server
- a multi-instance autoscaling service
- a shared multi-writer database workload

The current architecture is best treated as a scheduled batch renderer.