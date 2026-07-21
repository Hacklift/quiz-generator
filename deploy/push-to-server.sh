#!/usr/bin/env bash
# Ship the local working tree to the Hetzner server and deploy it.
# Run from the repo root (Git Bash on Windows works):
#   bash deploy/push-to-server.sh
set -euo pipefail

SERVER=root@178.105.196.254
APP_DIR=/opt/quiz-generator

cd "$(dirname "$0")/.."

echo "==> Copying code to $SERVER:$APP_DIR ..."
tar czf - \
    --exclude=.git \
    --exclude=node_modules \
    --exclude=.next \
    --exclude=__pycache__ \
    --exclude='*.pyc' \
    --exclude=.pytest_cache \
    . | ssh $SERVER "mkdir -p $APP_DIR && tar xzf - -C $APP_DIR"

echo "==> Running remote deploy..."
ssh $SERVER "bash $APP_DIR/deploy/deploy.sh"
