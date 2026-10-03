#!/bin/bash
# Start a fresh live shift on the local FryBird site (about a minute): run before a demo.
# Usage (from Windows):  wsl -d Ubuntu -- bash /mnt/c/Users/Cosmos/Documents/frybird/scripts/wsl/refresh-live.sh
set -e
export PATH="$HOME/.local/bin:$PATH"
SITE=frybird.localhost
rsync -a /mnt/c/Users/Cosmos/Documents/frybird/ury/setup/ ~/frappe-bench/apps/ury/ury/setup/
cd ~/frappe-bench/sites
../env/bin/python -c "
import frappe
frappe.init(site='$SITE'); frappe.connect()
from ury.setup import live_seed
live_seed.refresh_live()
"
cd .. && bench --site $SITE clear-cache
