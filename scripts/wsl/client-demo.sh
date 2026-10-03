#!/bin/bash
# Prepare the local FryBird site for a client to try through a tunnel (run with dev-start.sh running):
#   * creates/updates the demo login demo@frybird.test (password kept in WSL ~/.frybird_demo)
#   * starts a fresh live shift that belongs to the demo login, with the opening checklist pending
#   * turns developer mode off so errors don't show internals to visitors
# Then share:  cloudflared tunnel --url http://localhost:8080   (nginx on 8080 adds live updates)
# Usage (from Windows):  wsl -d Ubuntu -- bash /mnt/c/Users/Cosmos/Documents/frybird/scripts/wsl/client-demo.sh
set -e
export PATH="$HOME/.local/bin:$PATH"
SITE=frybird.localhost
DEMO_USER=demo@frybird.test

[ -f ~/.frybird_demo ] || { head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 10 > ~/.frybird_demo; chmod 600 ~/.frybird_demo; }
rsync -a /mnt/c/Users/Cosmos/Documents/frybird/ury/setup/ ~/frappe-bench/apps/ury/ury/setup/
cd ~/frappe-bench/sites
../env/bin/python -c "
import frappe
frappe.init(site='$SITE'); frappe.connect()
from ury.setup.demo_user import create_demo_user
from ury.setup import live_seed
create_demo_user('$DEMO_USER', 'FryBird Demo', open('$HOME/.frybird_demo').read().strip())
live_seed.refresh_live(user='$DEMO_USER')
"
cd ..
bench --site $SITE set-config developer_mode 0
bench --site $SITE clear-cache
echo "Demo login: $DEMO_USER  (password: wsl -d Ubuntu -- cat ~/.frybird_demo)"
