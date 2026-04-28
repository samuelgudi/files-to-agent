#!/usr/bin/env bash
#
# update-host.sh — host-side watcher for /update requests from the Docker bot.
#
# The bot, running inside the container, drops a flag file at
#   /var/lib/files-to-agent/update.requested
# which is mounted to ./update-flag on the host (see docker-compose.yml).
#
# This script polls that path, runs `docker compose pull && docker compose up -d`,
# and removes the flag.
#
# Install (systemd):
#   sudo cp scripts/update-host.sh /usr/local/bin/files-to-agent-update-host
#   sudo cp scripts/files-to-agent-update-host.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now files-to-agent-update-host
#
# Or run interactively from the repo dir:
#   bash scripts/update-host.sh
#
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
FLAG_DIR="${FLAG_DIR:-$COMPOSE_DIR/update-flag}"
FLAG_FILE="$FLAG_DIR/update.requested"
POLL_SECONDS="${POLL_SECONDS:-5}"

mkdir -p "$FLAG_DIR"

echo "[update-host] watching $FLAG_FILE (compose dir: $COMPOSE_DIR)"

while true; do
    if [[ -f "$FLAG_FILE" ]]; then
        echo "[update-host] flag detected at $(date -Iseconds), running update"
        rm -f "$FLAG_FILE"
        (
            cd "$COMPOSE_DIR"
            docker compose pull files-to-agent || docker compose pull
            docker compose up -d
        ) || echo "[update-host] update failed; will retry on next flag"
        echo "[update-host] update finished"
    fi
    sleep "$POLL_SECONDS"
done
