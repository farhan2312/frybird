#!/bin/bash
# FryBird production server install for a fresh Ubuntu 24.04 VM (Frappe/ERPNext/HRMS v15 + FryBird).
# Run as the VM's admin user (needs passwordless sudo), e.g. on Azure:
#   SITE=pos.frybird.ae ALIAS=frybird-pos.centralindia.cloudapp.azure.com bash install.sh
#
# Creates a clean store (no demo history) and leaves these secrets in the admin user's home (chmod 600):
#   ~/.frybird_db_root  MariaDB root password      ~/.frybird_admin  Administrator password
# HTTPS is a separate step once DNS points at the server (see scripts/server/README.md).
set -euo pipefail

SITE=${SITE:?set SITE, e.g. pos.frybird.ae}
ALIAS=${ALIAS:-}
REPO=${REPO:-https://github.com/farhan2312/frybird}
GIT_BRANCH=${GIT_BRANCH:-main}
COUNTRY=${COUNTRY:-United Arab Emirates}
TIMEZONE=${TIMEZONE:-Asia/Dubai}
CURRENCY=${CURRENCY:-AED}
COMPANY=${COMPANY:-FryBird LLC}
ABBR=${ABBR:-FB}
YEAR=$(date +%Y)
export DEBIAN_FRONTEND=noninteractive
log() { echo -e "\n==== $* ====\n"; }

log "System packages"
sudo apt-get update -q
sudo apt-get install -yq git curl build-essential pkg-config cron \
  mariadb-server mariadb-client libmariadb-dev redis-server nginx supervisor \
  xvfb libfontconfig1 fontconfig xfonts-75dpi xfonts-base certbot
if ! command -v wkhtmltopdf >/dev/null; then  # patched-qt build Frappe uses for PDF invoices
  curl -fsSL -o /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.jammy_amd64.deb \
    && sudo apt-get install -yq /tmp/wkhtmltox.deb || echo "wkhtmltopdf not installed (PDF printing only)"
fi

log "Swap (helps frontend builds on a small VM)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
  grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

log "MariaDB"
sudo tee /etc/mysql/mariadb.conf.d/99-frappe.cnf >/dev/null <<'EOF'
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
innodb_buffer_pool_size = 1G

[mysql]
default-character-set = utf8mb4
EOF
sudo systemctl restart mariadb
[ -f ~/.frybird_db_root ] || { head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' > ~/.frybird_db_root; chmod 600 ~/.frybird_db_root; }
[ -f ~/.frybird_admin ] || { head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' > ~/.frybird_admin; chmod 600 ~/.frybird_admin; }
DB_ROOT_PW=$(cat ~/.frybird_db_root)
sudo mariadb -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('$DB_ROOT_PW') OR unix_socket; FLUSH PRIVILEGES;"

log "Python 3.11 (uv), Node 20 (nvm), yarn, bench"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] || curl -fsSo- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
set +u; . "$NVM_DIR/nvm.sh"; set -u
nvm install 20 >/dev/null && nvm alias default 20 >/dev/null
command -v yarn >/dev/null || npm install -g yarn >/dev/null
uv tool install --python 3.11 frappe-bench 2>/dev/null || true

log "Bench and apps"
cd ~
[ -d frappe-bench ] || bench init --frappe-branch version-15 --python "$(uv python find 3.11)" frappe-bench
cd ~/frappe-bench
[ -d apps/erpnext ] || bench get-app --branch version-15 erpnext https://github.com/frappe/erpnext.git
[ -d apps/hrms ] || bench get-app --branch version-15 hrms https://github.com/frappe/hrms.git
[ -d apps/ury ] || bench get-app --branch "$GIT_BRANCH" ury "$REPO"
printf 'frappe\nerpnext\nhrms\nury\n' > sites/apps.txt
bench build

log "Production services (supervisor runs redis, workers, socketio; nginx in front)"
# before creating the site: new-site needs the bench redis instances, which supervisor starts
sudo env "PATH=$PATH" "NVM_DIR=$NVM_DIR" "$(command -v bench)" setup production "$USER" --yes
sudo supervisorctl status | head -20
for i in $(seq 1 20); do redis-cli -p 11000 ping >/dev/null 2>&1 && redis-cli -p 13000 ping >/dev/null 2>&1 && break; sleep 3; done

log "Site $SITE"
if [ ! -f "sites/$SITE/site_config.json" ]; then
  bench new-site "$SITE" --db-root-username root --db-root-password "$DB_ROOT_PW" \
    --admin-password "$(cat ~/.frybird_admin)" --install-app erpnext
  bench --site "$SITE" install-app hrms
  bench --site "$SITE" install-app ury
fi
bench use "$SITE"
bench --site "$SITE" set-config developer_mode 0

log "Company setup (ERPNext wizard, no demo data)"
bench --site "$SITE" execute frappe.desk.page.setup_wizard.setup_wizard.setup_complete --kwargs "{\"args\": {
  \"language\": \"English\", \"country\": \"$COUNTRY\", \"timezone\": \"$TIMEZONE\", \"currency\": \"$CURRENCY\",
  \"company_name\": \"$COMPANY\", \"company_abbr\": \"$ABBR\", \"chart_of_accounts\": \"Standard\",
  \"fy_start_date\": \"$YEAR-01-01\", \"fy_end_date\": \"$YEAR-12-31\", \"setup_ury_demo\": 0, \"setup_demo\": 0
}}"

log "FryBird store (menu, tables, kitchens, checklists, VAT, Talabat/Keeta, QR ordering)"
(cd sites && ../env/bin/python -c "
import frappe
frappe.init(site='$SITE'); frappe.connect()
from ury.setup.store_setup import setup_store
print(setup_store())
")

log "nginx for the site"
if [ -n "$ALIAS" ]; then
  bench setup add-domain "$ALIAS" --site "$SITE"
  bench setup nginx --yes
fi
bench setup nginx --yes
sudo nginx -t && sudo systemctl reload nginx
bench restart
bench setup backups
bench --site "$SITE" enable-scheduler

log "deploy.sh"
cp ~/frappe-bench/apps/ury/scripts/server/deploy.sh ~/deploy.sh && chmod +x ~/deploy.sh

log "Done: http://$SITE  ${ALIAS:+(also http://$ALIAS)}"
echo "Administrator password: cat ~/.frybird_admin"
