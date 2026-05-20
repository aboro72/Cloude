#!/bin/bash
# =============================================================================
# Cloude — One-Click Install Script
# Usage: curl -fsSL https://raw.githubusercontent.com/aboro72/Cloude/master/install.sh | sudo bash
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO_URL="https://github.com/aboro72/Cloude.git"
INSTALL_DIR="/home/storage/Cloude"
APP_USER="storage"
VENV_DIR="${INSTALL_DIR}/venv"
DJANGO_DIR="${INSTALL_DIR}/cloudservice"
PYTHON_MIN="3.11"

log()     { echo -e "${GREEN}[✓]${NC} $*"; }
info()    { echo -e "${BLUE}[→]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }
section() { echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n${BLUE}  $*${NC}\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# --- Root check --------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    error "Run this script as root: sudo bash install.sh"
fi

# --- OS check ----------------------------------------------------------------
if ! grep -qE "(Ubuntu|Debian)" /etc/os-release 2>/dev/null; then
    warn "This script targets Ubuntu 22.04+ / Debian 12. Proceeding anyway..."
fi

section "Cloude Installer"
echo "  Repo   : $REPO_URL"
echo "  Install: $INSTALL_DIR"
echo "  User   : $APP_USER"
echo ""
read -rp "  Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }

# --- System packages ---------------------------------------------------------
section "1/7  Installing system packages"
apt-get update -q
apt-get install -y -q \
    python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib \
    redis-server \
    nginx git \
    libpq-dev libmagic1 \
    build-essential curl
log "System packages installed"

# --- Python version check ----------------------------------------------------
PYTHON_BIN=$(command -v python3)
PY_VERSION=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)"; then
    log "Python $PY_VERSION found"
else
    error "Python 3.11+ required, found $PY_VERSION. Install it first: https://www.python.org"
fi

# --- Create app user ---------------------------------------------------------
section "2/7  Creating application user"
if id "$APP_USER" &>/dev/null; then
    log "User '$APP_USER' already exists"
else
    useradd -m -s /bin/bash "$APP_USER"
    log "User '$APP_USER' created"
fi

# --- Clone repository --------------------------------------------------------
section "3/7  Cloning repository"
if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Repo already exists — pulling latest changes"
    sudo -u "$APP_USER" git -C "$INSTALL_DIR" pull origin master
else
    sudo -u "$APP_USER" git clone "$REPO_URL" "$INSTALL_DIR"
fi
log "Repository ready at $INSTALL_DIR"

# --- Python virtualenv -------------------------------------------------------
section "4/7  Setting up Python environment"
if [[ ! -d "$VENV_DIR" ]]; then
    sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
fi
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "${INSTALL_DIR}/requirements.txt" -q
log "Python packages installed"

# --- Database ----------------------------------------------------------------
section "5/7  Setting up PostgreSQL database"
DB_NAME="cloudservice"
DB_USER="cloudservice"
DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
log "Database '${DB_NAME}' ready"

# --- Configure .env ----------------------------------------------------------
section "6/7  Configuring environment"
ENV_FILE="${DJANGO_DIR}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    cp "${INSTALL_DIR}/.env.example" "$ENV_FILE"
fi

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

echo ""
read -rp "  Your domain or IP (e.g. intranet.mycompany.com): " DOMAIN
[[ -z "$DOMAIN" ]] && DOMAIN="localhost"

# Write config
sudo -u "$APP_USER" tee "$ENV_FILE" > /dev/null <<EOF
DEBUG=False
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=${DOMAIN},localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/2

CLOUDSERVICE_EXTERNAL_URL=https://${DOMAIN}
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
DEFAULT_STORAGE_QUOTA=5368709120
EOF

log ".env configured"

# --- Django setup ------------------------------------------------------------
MANAGE="${VENV_DIR}/bin/python ${DJANGO_DIR}/manage.py"

info "Running database migrations..."
sudo -u "$APP_USER" $MANAGE migrate --noinput

info "Collecting static files..."
sudo -u "$APP_USER" $MANAGE collectstatic --noinput -v 0

log "Django setup complete"

# --- Systemd services --------------------------------------------------------
section "7/7  Installing systemd services and Nginx"

for svc in gunicorn daphne; do
    cp "${INSTALL_DIR}/${svc}.service" /etc/systemd/system/
done

# Fix paths in service files if needed
sed -i "s|/home/storage/Cloude|${INSTALL_DIR}|g" /etc/systemd/system/gunicorn.service
sed -i "s|/home/storage/Cloude|${INSTALL_DIR}|g" /etc/systemd/system/daphne.service

systemctl daemon-reload
systemctl enable --now gunicorn daphne
systemctl enable --now redis-server postgresql
log "Services enabled and started"

# Nginx
cp "${INSTALL_DIR}/nginx.conf" /etc/nginx/sites-available/cloude
sed -i "s|server_name .*;|server_name ${DOMAIN};|g" /etc/nginx/sites-available/cloude
ln -sf /etc/nginx/sites-available/cloude /etc/nginx/sites-enabled/cloude
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
log "Nginx configured"

# --- Create superuser --------------------------------------------------------
section "Create your admin account"
echo ""
echo "  Create the first admin user for the web interface:"
echo ""
sudo -u "$APP_USER" $MANAGE createsuperuser

# --- Done --------------------------------------------------------------------
section "Installation complete!"
echo ""
echo -e "  ${GREEN}Cloude is running!${NC}"
echo ""
echo "  Web interface : http://${DOMAIN}/"
echo "  Admin panel   : http://${DOMAIN}/admin/"
echo "  API docs      : http://${DOMAIN}/api/docs/"
echo ""
echo "  Check service status:"
echo "    sudo systemctl status gunicorn daphne"
echo ""
echo "  View logs:"
echo "    sudo journalctl -u gunicorn -f"
echo ""
if [[ "$DOMAIN" == "localhost" ]]; then
    warn "You entered 'localhost'. To make Cloude accessible from other machines,"
    warn "re-run the script with your server's IP or domain name."
fi
echo ""
