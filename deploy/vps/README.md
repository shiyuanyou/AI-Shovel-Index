# VPS Deployment Kit

This directory contains a concrete deployment path for the recommended target:
Ubuntu VPS + systemd timer.

## Files

- `bootstrap_ubuntu.sh`: base server bootstrap for Ubuntu
- `../systemd/ai-shovel-index.service`: systemd service template
- `../systemd/ai-shovel-index.timer`: systemd timer template

## Recommended Defaults

- app user: `ai-shovel`
- app dir: `/opt/ai-shovel-index`
- schedule: `02:00 UTC` daily (`10:00` Beijing time)
- persistence: local `data/index.db` on the VPS

## 1. Bootstrap The Server

Run this on the VPS as a sudo-capable user:

```bash
cd /path/to/repo/deploy/vps
chmod +x bootstrap_ubuntu.sh
REPO_URL=git@github.com:YOUR_NAME/AI-Shovel-Index.git ./bootstrap_ubuntu.sh
```

If your server uses a different Python binary or install path:

```bash
APP_USER=ai-shovel \
APP_DIR=/opt/ai-shovel-index \
PYTHON_BIN=python3.12 \
REPO_URL=git@github.com:YOUR_NAME/AI-Shovel-Index.git \
./bootstrap_ubuntu.sh
```

## 2. Install systemd Units

Replace placeholders in the service template:

```bash
APP_DIR=/opt/ai-shovel-index
APP_USER=ai-shovel

sed \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  -e "s|__APP_USER__|${APP_USER}|g" \
  ../systemd/ai-shovel-index.service | sudo tee /etc/systemd/system/ai-shovel-index.service >/dev/null

sudo cp ../systemd/ai-shovel-index.timer /etc/systemd/system/ai-shovel-index.timer
sudo systemctl daemon-reload
```

## 3. First Manual Verification

Run these before enabling the timer:

```bash
sudo -u ai-shovel -- /opt/ai-shovel-index/.venv/bin/python3 /opt/ai-shovel-index/smoke_test.py
sudo -u ai-shovel -- /opt/ai-shovel-index/.venv/bin/python3 /opt/ai-shovel-index/run_daily.py --date 2026-03-06
```

Check logs:

```bash
journalctl -u ai-shovel-index.service -n 200 --no-pager
```

Look for these markers in stdout logs:

- `RUN_CONTEXT`
- `CRAWL_SUMMARY`
- `CRAWL_HEALTH`
- `ANALYSIS_SUMMARY`
- `OUTPUT_SUMMARY`

## 4. Enable Daily Scheduling

```bash
sudo systemctl enable --now ai-shovel-index.timer
sudo systemctl list-timers ai-shovel-index.timer
```

To trigger one run immediately:

```bash
sudo systemctl start ai-shovel-index.service
```

## 5. Updating The Deployment

```bash
sudo -u ai-shovel -- git -C /opt/ai-shovel-index pull --ff-only
sudo -u ai-shovel -- /opt/ai-shovel-index/.venv/bin/pip install -r /opt/ai-shovel-index/requirements.txt
sudo -u ai-shovel -- /opt/ai-shovel-index/.venv/bin/playwright install chromium
sudo systemctl restart ai-shovel-index.timer
```

## Notes

- The service writes runtime state to local `data/` and `output/`.
- Do not depend on git commits of `data/index.db` for VPS persistence.
- The service currently runs as a single-host batch job; avoid multiple timers or multiple hosts pointing at the same SQLite file.
