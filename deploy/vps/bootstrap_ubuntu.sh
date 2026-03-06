#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-ai-shovel}"
APP_DIR="${APP_DIR:-/opt/ai-shovel-index}"
REPO_URL="${REPO_URL:-}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if [[ -z "$REPO_URL" ]]; then
  echo "REPO_URL is required, for example:"
  echo "  REPO_URL=git@github.com:YOUR_NAME/AI-Shovel-Index.git $0"
  exit 1
fi

sudo apt-get update
sudo apt-get install -y \
  git \
  "$PYTHON_BIN" \
  "${PYTHON_BIN}-venv" \
  python3-pip \
  fontconfig \
  fonts-noto-cjk

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --home-dir "$APP_DIR" --shell /bin/bash "$APP_USER"
fi

sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

if [[ ! -d "$APP_DIR/.git" ]]; then
  sudo -u "$APP_USER" -- git clone "$REPO_URL" "$APP_DIR"
else
  sudo -u "$APP_USER" -- git -C "$APP_DIR" pull --ff-only
fi

sudo -u "$APP_USER" -- mkdir -p "$APP_DIR/data" "$APP_DIR/output" "$APP_DIR/logs"
sudo -u "$APP_USER" -- "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" -- "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" -- "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
sudo "$APP_DIR/.venv/bin/python3" -m playwright install-deps chromium
sudo -u "$APP_USER" -- "$APP_DIR/.venv/bin/playwright" install chromium
sudo -u "$APP_USER" -- "$APP_DIR/.venv/bin/python3" "$APP_DIR/smoke_test.py"

echo "Bootstrap complete for $APP_DIR"
