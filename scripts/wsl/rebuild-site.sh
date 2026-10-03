#!/bin/bash
# Drop and recreate the local FryBird demo site (UAE / AED) with live-looking data.
# Usage (from Windows):  wsl -d Ubuntu -- bash /mnt/c/Users/Cosmos/Documents/frybird/scripts/wsl/rebuild-site.sh [history_days]
# Keep dev-start.sh running in another window: shift closings consolidate in background workers.
set -e
export PATH="$HOME/.local/bin:$PATH"
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"
SITE=frybird.localhost
DAYS=${1:-21}
BENCH=~/frappe-bench

bash /mnt/c/Users/Cosmos/Documents/frybird/scripts/wsl/dev-sync.sh none || true
cd "$BENCH"

DB_ROOT_PW="$(cat ~/.frybird_db_root)"
[ -f ~/.frybird_admin ] || { head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' > ~/.frybird_admin; chmod 600 ~/.frybird_admin; }

if [ -f "sites/$SITE/site_config.json" ]; then
  bench drop-site $SITE --force --no-backup --db-root-username root --db-root-password "$DB_ROOT_PW"
fi
rm -rf "sites/$SITE"  # a running bench recreates sites/<site>/logs right after the drop
bench new-site $SITE --db-root-username root --db-root-password "$DB_ROOT_PW" \
  --admin-password "$(cat ~/.frybird_admin)" --install-app erpnext
bench --site $SITE install-app hrms
bench --site $SITE install-app ury
bench use $SITE
bench --site $SITE set-config developer_mode 1

bench --site $SITE execute frappe.desk.page.setup_wizard.setup_wizard.setup_complete --kwargs '{"args": {
  "language": "English", "country": "United Arab Emirates", "timezone": "Asia/Dubai", "currency": "AED",
  "company_name": "FryBird LLC", "company_abbr": "FB", "chart_of_accounts": "Standard",
  "fy_start_date": "2026-01-01", "fy_end_date": "2026-12-31",
  "setup_ury_demo": 1, "setup_demo": 0
}}'
# run in-process: `bench execute ury.*` can fail with "name 'ury' is not defined" right after the wizard
(cd sites && ../env/bin/python -c "
import frappe
frappe.init(site='$SITE'); frappe.connect()
from ury.install import set_frybird_branding
from ury.setup import live_seed
set_frybird_branding(); frappe.db.commit()
live_seed.run(history_days=$DAYS)
")
bench --site $SITE clear-cache
echo "REBUILD_OK"
