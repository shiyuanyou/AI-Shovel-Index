#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-build}"
ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.yml}"

case "$MODE" in
  build)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build ai-shovel-index ai-shovel-smoke
    ;;
  pull)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull ai-shovel-index ai-shovel-smoke
    ;;
  *)
    echo "Usage: $0 [build|pull]"
    exit 1
    ;;
esac

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm ai-shovel-smoke

echo "Image refresh complete via mode=$MODE"
