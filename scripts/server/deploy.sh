#!/bin/bash
# Update FryBird on the production server from GitHub.
#   bash ~/deploy.sh            # deploy the latest main
#   bash ~/deploy.sh <commit>   # deploy (or roll back to) a specific commit
# Steps: backup -> pull -> python/node deps -> build -> migrate -> restart. Logs in ~/deploy-logs/.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export NVM_DIR="$HOME/.nvm"; set +u; . "$NVM_DIR/nvm.sh"; set -u

REF=${1:-origin/main}
BENCH=~/frappe-bench
mkdir -p ~/deploy-logs
LOG=~/deploy-logs/deploy-$(date +%Y%m%d-%H%M%S).log
exec > >(tee -a "$LOG") 2>&1

cd "$BENCH"
SITE=$(cat sites/currentsite.txt)
echo "== Deploying $REF to $SITE ($(date))"

echo "== Backup"
bench --site "$SITE" backup --with-files

echo "== Pull"
cd apps/ury
git fetch --quiet origin
BEFORE=$(git rev-parse --short HEAD)
git reset --hard "$REF"
AFTER=$(git rev-parse --short HEAD)
echo "   $BEFORE -> $AFTER"
git log --oneline "$BEFORE..$AFTER" 2>/dev/null | head -20 || true

echo "== Dependencies and build"
cd "$BENCH"
./env/bin/python -m pip install --quiet -e apps/ury
(cd apps/ury && yarn install --silent --network-timeout 600000)
bench build --app ury

echo "== Migrate"
bench --site "$SITE" migrate

echo "== Restart"
bench restart
bench --site "$SITE" clear-cache
echo "== Done: $AFTER is live (log: $LOG)"
