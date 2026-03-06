#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-ai-shovel}"
APP_DIR="${APP_DIR:-/opt/ai-shovel-index}"
REPO_URL="${REPO_URL:-}"
RUNTIME_DIR="${RUNTIME_DIR:-$APP_DIR/runtime}"

if [[ -z "$REPO_URL" ]]; then
  echo "REPO_URL is required, for example:"
  echo "  REPO_URL=git@github.com:YOUR_NAME/AI-Shovel-Index.git $0"
  exit 1
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl git gnupg lsb-release

if ! command -v docker >/dev/null 2>&1; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --home-dir "$APP_DIR" --shell /bin/bash "$APP_USER"
fi

sudo usermod -aG docker "$APP_USER"
sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

if [[ ! -d "$APP_DIR/.git" ]]; then
  sudo -u "$APP_USER" -- git clone "$REPO_URL" "$APP_DIR"
else
  sudo -u "$APP_USER" -- git -C "$APP_DIR" pull --ff-only
fi

sudo -u "$APP_USER" -- mkdir -p "$RUNTIME_DIR/data" "$RUNTIME_DIR/output" "$RUNTIME_DIR/logs"

if [[ ! -f "$APP_DIR/deploy/docker/.env" ]]; then
  sudo -u "$APP_USER" -- cp "$APP_DIR/deploy/docker/.env.example" "$APP_DIR/deploy/docker/.env"
fi

sudo chmod +x "$APP_DIR/deploy/docker/refresh_image.sh"

sudo sed -i.bak \
  -e "s|^AI_SHOVEL_DATA_DIR=.*|AI_SHOVEL_DATA_DIR=$RUNTIME_DIR/data|" \
  -e "s|^AI_SHOVEL_OUTPUT_DIR=.*|AI_SHOVEL_OUTPUT_DIR=$RUNTIME_DIR/output|" \
  "$APP_DIR/deploy/docker/.env"

sudo systemctl enable docker
sudo systemctl start docker

sudo -u "$APP_USER" -- sh -lc "cd '$APP_DIR/deploy/docker' && ./refresh_image.sh build"

echo "Docker host bootstrap complete for $APP_DIR"
