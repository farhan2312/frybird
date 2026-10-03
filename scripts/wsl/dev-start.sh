#!/bin/bash
# Start the local FryBird bench in WSL: http://frybird.localhost:8000
# Usage (from Windows):  wsl -d Ubuntu -- bash /mnt/c/Users/Cosmos/Documents/frybird/scripts/wsl/dev-start.sh
set -e
export PATH="$HOME/.local/bin:$PATH"
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"
sudo -n service mariadb start >/dev/null 2>&1 || true
cd ~/frappe-bench
exec bench start
