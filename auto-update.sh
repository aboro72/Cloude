#!/bin/bash
# =============================================================================
# Cloude – Automatisches GitHub-Update
# =============================================================================
# Installationsanleitung (einmalig auf dem Server als root):
#
#   cp /home/storage/Cloude/auto-update.sh /usr/local/bin/cloude-auto-update.sh
#   chmod +x /usr/local/bin/cloude-auto-update.sh
#   cp /home/storage/Cloude/auto-update.service /etc/systemd/system/
#   cp /home/storage/Cloude/auto-update.timer  /etc/systemd/system/
#   touch /var/log/cloude-autoupdate.log
#   chown storage:storage /var/log/cloude-autoupdate.log
#   systemctl daemon-reload
#   systemctl enable --now auto-update.timer
# =============================================================================

set -euo pipefail

REPO_DIR="/home/storage/Cloude"
VENV_PIP="${REPO_DIR}/venv/bin/pip"
VENV_PYTHON="${REPO_DIR}/venv/bin/python"
DJANGO_DIR="${REPO_DIR}/cloudservice"
LOG_FILE="/var/log/cloude-autoupdate.log"
BRANCH="master"
APP_USER="storage"

# Services die neugestartet werden sollen (in Reihenfolge)
SERVICES=("gunicorn.service" "daphne.service" "celery.service" "celery-beat.service")

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

run_as_user() {
    sudo -u "$APP_USER" "$@"
}

restart_service() {
    local svc="$1"
    if systemctl is-active --quiet "$svc" 2>/dev/null || systemctl is-enabled --quiet "$svc" 2>/dev/null; then
        log "Starte $svc neu..."
        systemctl restart "$svc"
    else
        log "Dienst $svc nicht aktiv – übersprungen."
    fi
}

# ------------------------------------------------------------------------------
log "======================================================="
log "  Cloude Auto-Update gestartet"
log "======================================================="

# Aktuelle Commits von GitHub holen (ohne zu mergen)
log "Prüfe GitHub (origin/$BRANCH) auf neue Commits..."
run_as_user git -C "$REPO_DIR" fetch origin "$BRANCH" 2>&1 | tee -a "$LOG_FILE"

LOCAL=$(run_as_user git -C "$REPO_DIR" rev-parse HEAD)
REMOTE=$(run_as_user git -C "$REPO_DIR" rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Kein Update notwendig. Aktueller Stand: ${LOCAL:0:8}"
    exit 0
fi

log "Neuer Stand verfügbar: ${LOCAL:0:8} → ${REMOTE:0:8}"

# Git-Pull
log "------------------------------------------------------"
log "git pull..."
run_as_user git -C "$REPO_DIR" pull origin "$BRANCH" 2>&1 | tee -a "$LOG_FILE"

# Python-Abhängigkeiten
log "------------------------------------------------------"
log "pip install -r requirements.txt..."
run_as_user "$VENV_PIP" install -r "${REPO_DIR}/requirements.txt" 2>&1 | tee -a "$LOG_FILE"

# Datenbankmigrationen
log "------------------------------------------------------"
log "manage.py migrate..."
run_as_user "$VENV_PYTHON" "${DJANGO_DIR}/manage.py" migrate --noinput 2>&1 | tee -a "$LOG_FILE"

# Statische Dateien
log "------------------------------------------------------"
log "manage.py collectstatic..."
run_as_user "$VENV_PYTHON" "${DJANGO_DIR}/manage.py" collectstatic --noinput 2>&1 | tee -a "$LOG_FILE"

# Dienste neu starten
log "------------------------------------------------------"
for svc in "${SERVICES[@]}"; do
    restart_service "$svc"
done

log "======================================================="
log "  Update erfolgreich abgeschlossen!"
log "======================================================="
