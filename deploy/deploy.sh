#!/usr/bin/env bash
# Deploy / update Quiz Generator. Run as root on the server from anywhere:
#   bash /opt/quiz-generator/deploy/deploy.sh
#
# The server has no GitHub access, so this script deploys whatever code is
# already in /opt/quiz-generator. Ship fresh code from your dev machine with:
#   bash deploy/push-to-server.sh   (runs this script for you afterwards)
set -euo pipefail

APP_DIR=/opt/quiz-generator
COMPOSE="docker compose -f docker-compose.prod.yml"

cd $APP_DIR

echo "==> Building images..."
$COMPOSE build

echo "==> Starting / updating containers..."
$COMPOSE up -d --remove-orphans

echo "==> Syncing category seed data (idempotent)..."
$COMPOSE run --rm seed-categories

echo "==> Refreshing nginx config..."
if ! cmp -s deploy/nginx-quiz-campilot.conf /etc/nginx/sites-available/quiz-campilot; then
    cp deploy/nginx-quiz-campilot.conf /etc/nginx/sites-available/quiz-campilot
    ln -sf /etc/nginx/sites-available/quiz-campilot /etc/nginx/sites-enabled/quiz-campilot
    nginx -t
    systemctl reload nginx
    echo "    nginx config updated and reloaded."
else
    echo "    nginx config unchanged."
fi

echo "==> Health checks..."
sleep 5
curl -sf -o /dev/null http://127.0.0.1:8020/api && echo "    API      OK (127.0.0.1:8020)"
curl -sf -o /dev/null http://127.0.0.1:3020/    && echo "    Frontend OK (127.0.0.1:3020)"

echo ""
echo "=== Deploy complete ==="
$COMPOSE ps --format 'table {{.Name}}\t{{.Status}}'
