#!/bin/bash
# Start the local FryBird bench in WSL: http://frybird.localhost:8000
# Usage (from Windows):  wsl -d Ubuntu -- bash /mnt/c/Users/Cosmos/Documents/frybird/scripts/wsl/dev-start.sh
set -e
export PATH="$HOME/.local/bin:$PATH"
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"
cd ~/frappe-bench

if ss -ltn 2>/dev/null | grep -qE ":(8000|9000) "; then
  echo "FryBird is already running (port 8000/9000 in use): open http://frybird.localhost:8000"
  echo "To restart it, stop the old one first:  wsl -d Ubuntu -- pkill -f 'honcho start'"
  exit 1
fi

sudo -n service mariadb start >/dev/null 2>&1 || true
# bench's Procfile has no redis entries (bench was set up with --skip-redis-config-generation), so start them here
for c in redis_cache redis_queue; do
  port=$(grep -oP '^port \K\d+' config/$c.conf)
  redis-cli -p "$port" ping >/dev/null 2>&1 || redis-server config/$c.conf --daemonize yes >/dev/null
done

exec bench start
