#!/usr/bin/env bash
# Deploy / update Quiz Generator. Run as root on the server from anywhere:
#   bash /opt/quiz-generator/deploy/deploy.sh
#
# Pulls the latest master via the read-only deploy key, then rebuilds and
# restarts the stack. Secrets stay in /opt/quiz-generator/.env (gitignored).
set -euo pipefail

main() {
    APP_DIR=/opt/quiz-generator
    REPO=git@github.com:Hacklift/quiz-generator.git
    DEPLOY_KEY=/root/.ssh/quiz_generator_deploy
    COMPOSE="docker compose -f docker-compose.prod.yml"

    cd $APP_DIR

    echo "==> Pulling latest code from master..."
    if [ ! -d .git ]; then
        git init -b master
        git remote add origin $REPO
        git config core.sshCommand "ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes"
    fi
    git fetch origin master
    git reset --hard origin/master
    # Drop untracked leftovers; ignored files (.env) are untouched.
    git clean -fd

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
}

main "$@"
