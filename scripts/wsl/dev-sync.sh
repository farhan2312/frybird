#!/bin/bash
# Copy edits from the Windows checkout into the WSL bench and rebuild what changed.
# Usage (from Windows):  wsl -d Ubuntu -- bash /mnt/c/Users/Cosmos/Documents/frybird/scripts/wsl/dev-sync.sh [pos|ury|order|mosaic|urypos|all|none]
#   pos/ury/order/mosaic/urypos  rebuild just that frontend (ury = admin app in frontend/, order = self-order/)
#   all                          rebuild every frontend
#   none (default)               Python/JSON only; also runs migrate so doctype/fixture changes apply
set -e
export PATH="$HOME/.local/bin:$PATH"
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"
SRC=/mnt/c/Users/Cosmos/Documents/frybird
BENCH=~/frappe-bench
SITE=frybird.localhost

rsync -a --delete \
  --exclude node_modules --exclude .claude \
  --exclude ury/public/pos --exclude ury/public/ury --exclude ury/public/urypos \
  --exclude ury/public/mosaic --exclude ury/public/order --exclude 'ury/www/pos.html' --exclude 'ury/www/ury.html' --exclude 'ury/www/urypos.html' --exclude 'ury/www/mosaic.html' --exclude 'ury/www/order.html' \
  "$SRC/" "$BENCH/apps/ury/"

cd "$BENCH/apps/ury"
case "${1:-none}" in
  pos)    yarn ury-posv2-build ;;
  ury)    yarn ury-frontend-build ;;
  order)  yarn ury-self-order-build ;;
  mosaic) yarn ury-mosaic-build ;;
  urypos) yarn ury-pos-build ;;
  all)    yarn build ;;
  none)   ;;
  *) echo "unknown target: $1"; exit 1 ;;
esac

cd "$BENCH"
[ "${1:-none}" = none ] && bench --site $SITE migrate
bench --site $SITE clear-cache
echo "synced (${1:-none})"
