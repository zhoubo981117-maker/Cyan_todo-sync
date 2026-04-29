#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/Cyan_todo-sync}"
BRANCH="${BRANCH:-main}"
SERVICE="${SERVICE:-todo-sync}"

cd "$APP_DIR"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Working tree is dirty in $APP_DIR; refusing to update." >&2
  exit 1
fi

current="$(git rev-parse HEAD)"
echo "Current local commit: $current"
git fetch origin "$BRANCH"
remote="$(git rev-parse "origin/$BRANCH")"
echo "Current remote commit: $remote"

if [ "$current" = "$remote" ]; then
  echo "Already up to date: $current"
  exit 0
fi

git merge --ff-only "origin/$BRANCH"
new_current="$(git rev-parse HEAD)"
echo "Merged $current -> $new_current"
systemctl restart "$SERVICE"
echo "Restarted service: $SERVICE"

if systemctl is-active --quiet caddy; then
  systemctl reload caddy
  echo "Reloaded caddy"
fi

echo "Updated $APP_DIR from $current to $remote and restarted $SERVICE."
