#!/bin/bash
# Update FryBird on the production server from GitHub.
#   bash ~/deploy.sh            # deploy the latest main from GitHub
#   bash ~/deploy.sh <commit>   # deploy (or roll back to) a specific commit
# Steps: backup -> pull -> python/node deps -> build -> migrate -> restart. Logs in ~/deploy-logs/.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export NVM_DIR="$HOME/.nvm"; set +u; . "$NVM_DIR/nvm.sh"; set -u

REF=${1:-}
BENCH=~/frappe-bench
mkdir -p ~/deploy-logs
LOG=~/deploy-logs/deploy-$(date +%Y%m%d-%H%M%S).log
exec > >(tee -a "$LOG") 2>&1

cd "$BENCH"
SITE=${SITE:-$(cat sites/currentsite.txt 2>/dev/null || true)}
SITE=${SITE:-$(python3 -c "import json; print(json.load(open('sites/common_site_config.json')).get('default_site', ''))")}
SITE=${SITE:-$(ls -d sites/*/site_config.json | head -1 | cut -d/ -f2)}
echo "== Deploying ${REF:-latest main} to $SITE ($(date))"

echo "== Backup"
bench --site "$SITE" backup --with-files

echo "== Pull"
cd apps/ury
REMOTE=$(git remote | head -1)  # bench get-app names it "upstream"
REF=${REF:-$REMOTE/main}
git fetch --quiet "$REMOTE"
BEFORE=$(git rev-parse --short HEAD)
git reset --hard "$REF"
AFTER=$(git rev-parse --short HEAD)
echo "   $BEFORE -> $AFTER"
git log --oneline "$BEFORE..$AFTER" 2>/dev/null | head -20 || true

echo "== Dependencies and build"
cd "$BENCH"
# The app is installed in editable mode, so the server already runs the pulled code. Reinstalling only matters
# when the dependency files change, and it downloads build tools from pypi, which often times out from this VM.
changed() { [ "$BEFORE" = "$AFTER" ] && return 1; ! git -C apps/ury diff --quiet "$BEFORE" "$AFTER" -- "$@"; }
if changed pyproject.toml setup.py requirements.txt; then
  for try in 1 2 3; do
    ./env/bin/python -m pip install --quiet --timeout 60 -e apps/ury && break
    [ "$try" = 3 ] && { echo "pip install failed 3 times"; exit 1; }
    echo "   pip install failed, retrying ($try/3)"; sleep 10
  done
else
  echo "   Python dependencies unchanged, skipping pip install"
fi
if changed package.json yarn.lock '*/package.json' '*/yarn.lock'; then
  (cd apps/ury && yarn install --silent --network-timeout 600000)
else
  echo "   Node dependencies unchanged, skipping yarn install"
fi
bench build --app ury

echo "== Migrate"
bench --site "$SITE" migrate

echo "== Restart"
bench restart
bench --site "$SITE" clear-cache
echo "== Done: $AFTER is live (log: $LOG)"
