# STM: v1 — Cloud Deployment Readiness

**Version goal**: stabilize the project for cloud deployment, remove current doc and workflow drift, and reduce the chance of hidden failures in the daily batch pipeline.

**Created**: 2026-03-06  
**Current status**: BUILD

## Current Diagnosis

- The real product is now a 3-card renderer, but parts of the docs still describe older 4-card behavior.
- CI still includes a legacy Node/Tailwind build path that the active templates do not use.
- Runtime code is functional, but deployment concerns such as timezone clarity, SQLite single-writer assumptions, and render validation are not yet hardened.
- The project can already run daily, but it is not yet packaged as a clean cloud-ready batch service.

## Phase 1: Planning And Documentation

- [x] Refactor `AGENTS.md` into a concise, current workspace instruction file
- [x] Sync `docs/architecture.md` to the actual 3-card pipeline and current runtime assumptions
- [x] Add a dedicated deployment guide covering Python, Playwright, fonts, writable directories, and scheduler expectations
- [x] Decide the first deployment target: GitHub Actions only, VPS cron, Docker container, or managed cloud runtime

## Phase 2: Runtime Hardening

- [x] Make runtime date handling explicit and timezone-safe across `crawler.py`, `analyzer.py`, and `run_daily.py`
- [x] Define and implement the SQLite journal/concurrency strategy for single-run scheduling
- [x] Add clear render output validation so partial PNG generation fails fast
- [x] Add startup validation for required templates and critical directories

## Phase 3: CI And Delivery Simplification

- [x] Remove legacy Node/Tailwind steps from `.github/workflows/daily.yml` unless a task explicitly uses `templates/card.html`
- [x] Align CI commands with repo conventions by using `.venv` or document why CI intentionally differs
- [x] Add a deployment smoke test path for server verification

## Phase 4: Operability

- [x] Add crawler failure threshold warnings so systemic crawl breakage is visible quickly
- [x] Review logging for cloud execution and make sure failures are easy to diagnose from stdout logs
- [x] Decide whether `data/index.db` should keep being committed to git or move to server persistence

## Acceptance Criteria

- [ ] Documentation matches the real pipeline, outputs, and commands
- [ ] One clean daily run can execute in the target deployment environment without manual intervention
- [ ] Rendered cards are visually stable on the deployment OS
- [ ] Failure modes are explicit enough that a broken crawl or render is easy to detect
