# Cloude – Django Cloud Storage

Ein moderner Cloud-Speicherdienst auf Basis von Django 6, Gunicorn, Daphne und Celery.

**Entwickelt von Andreas Borowczak | [Aboro IT](https://aboro-it.de)**

---

## Changelog / Projektbereinigung

### Entfernte Bestandteile

| Entfernt | Grund |
|---|---|
| `Dockerfile` | Docker wird nicht mehr unterstützt |
| `docker-compose.yml` | Docker wird nicht mehr unterstützt |
| `unified-install/` | Docker-basiertes Setup-Wizard entfernt |
| `README_MIGRATION.md` | Veraltete Migrationsdokumentation |
| `MIGRATION_GUIDE_HELPDESK.md` | Nicht projektrelevant |
| `cloudservice/storage/*.bak.*` | Automatisch erstellte Backup-Dateien |

### Hinzugefügte Bestandteile

| Datei | Beschreibung |
|---|---|
| `auto-update.sh` | Automatisches Update-Skript (GitHub → Server) |
| `auto-update.service` | Systemd Service für das Update-Skript |
| `auto-update.timer` | Systemd Timer (alle 5 Minuten) |
| `auto-update.sudoers` | Optionale Sudoers-Regel für manuelle Ausführung |

---

## Features

- **Dateiverwaltung** – Upload, Download, Verschieben, Umbenennen, Versionen
- **Ordnerstruktur** – Hierarchische Ordner mit Breadcrumb-Navigation
- **Dateivorschau** – Bilder, Videos, Audio, PDFs direkt im Browser
- **Papierkorb** – Soft-Delete mit Wiederherstellung
- **Freigaben** – Öffentliche Links mit Passwortschutz und Ablaufdatum
- **Plugin-System** – Erweiterbar durch Hook-basierte Plugins
- **WebSocket** – Echtzeit-Benachrichtigungen über Daphne/Channels
- **REST-API** – Vollständige API mit JWT-Authentifizierung
- **Auto-Update** – Automatische Aktualisierung vom GitHub Master-Branch

---

## Projektstruktur

```
Cloude/
├── cloudservice/          # Django-Projekt
│   ├── accounts/          # Benutzerverwaltung & Profile
│   ├── api/               # REST-API (DRF)
│   ├── config/            # Django-Konfiguration (settings, urls, wsgi, asgi)
│   ├── core/              # Dashboard, WebSocket-Consumer, Celery-Tasks
│   ├── plugins/           # Plugin-System (Loader, Hooks, Admin)
│   ├── sharing/           # Dateifreigaben & öffentliche Links
│   ├── storage/           # Dateispeicher-Verwaltung
│   ├── templates/         # HTML-Templates
│   ├── static/            # CSS, JS, Bilder (Quellen)
│   └── manage.py
├── django-platform-auth/  # Eigenes Authentifizierungs-Modul
├── plugins/               # Installierte & paketierte Plugins
│   └── installed/
│       ├── clock_preview/
│       ├── collabora_online/
│       ├── mysite_hub/
│       ├── rss_feed/
│       └── weather/
├── requirements.txt       # Python-Abhängigkeiten
├── .env.example           # Umgebungsvariablen-Vorlage
├── gunicorn.service       # Systemd Service (WSGI)
├── daphne.service         # Systemd Service (ASGI/WebSocket)
├── demo-password-reset.service  # Systemd Service (Demo-Reset)
├── demo-password-reset.timer    # Systemd Timer (alle 30 Min.)
├── auto-update.service    # Systemd Service (GitHub-Update)
├── auto-update.timer      # Systemd Timer (alle 5 Min.)
├── auto-update.sh         # Update-Skript
├── nginx.conf             # Nginx-Konfiguration
└── nginx-proxy.conf       # Nginx Proxy-Konfiguration
```

---

## Systemanforderungen

- Ubuntu/Debian Linux
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Nginx
- git

---

## Installation (Linux-Server)

### 1. Benutzer und Repository

```bash
sudo useradd -m -s /bin/bash storage
sudo su - storage

git clone https://github.com/aboro72/Cloude.git
cd Cloude

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Umgebung konfigurieren

```bash
cp .env.example cloudservice/.env
nano cloudservice/.env
```

Wichtige Variablen:

```env
DEBUG=False
SECRET_KEY=<langer-geheimer-schluessel>
ALLOWED_HOSTS=deine-domain.de
DB_NAME=cloudservice
DB_USER=postgres
DB_PASSWORD=<passwort>
DB_HOST=localhost
REDIS_URL=redis://localhost:6379/0
```

### 3. Datenbank & statische Dateien

```bash
cd cloudservice
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 4. Systemd Services einrichten

```bash
# Als root:
sudo cp /home/storage/Cloude/gunicorn.service       /etc/systemd/system/
sudo cp /home/storage/Cloude/daphne.service         /etc/systemd/system/
sudo cp /home/storage/Cloude/demo-password-reset.service /etc/systemd/system/
sudo cp /home/storage/Cloude/demo-password-reset.timer   /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn daphne
sudo systemctl enable --now demo-password-reset.timer
```

### 5. Nginx konfigurieren

```bash
sudo cp /home/storage/Cloude/nginx.conf /etc/nginx/sites-available/cloude
sudo ln -s /etc/nginx/sites-available/cloude /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Auto-Update (GitHub → Server)

Das Auto-Update-System prüft alle **5 Minuten** ob es neue Commits im `master`-Branch gibt und aktualisiert den Server automatisch.

### Was passiert bei einem Update

1. `git fetch origin master` – neuen Stand prüfen (ohne zu mergen)
2. Vergleich `HEAD` vs. `origin/master` – kein Pull wenn nichts Neues
3. `git pull` – Änderungen einspielen
4. `pip install -r requirements.txt` – neue Abhängigkeiten installieren
5. `manage.py migrate` – Datenbankmigrationen ausführen
6. `manage.py collectstatic` – statische Dateien aktualisieren
7. Dienste neu starten (gunicorn, daphne, celery, celery-beat)

### Installation des Auto-Updates

```bash
# Als root:
cp /home/storage/Cloude/auto-update.sh /usr/local/bin/cloude-auto-update.sh
chmod +x /usr/local/bin/cloude-auto-update.sh

cp /home/storage/Cloude/auto-update.service /etc/systemd/system/
cp /home/storage/Cloude/auto-update.timer   /etc/systemd/system/

touch /var/log/cloude-autoupdate.log
chown storage:storage /var/log/cloude-autoupdate.log

systemctl daemon-reload
systemctl enable --now auto-update.timer
```

### Status & Logs prüfen

```bash
systemctl status auto-update.timer
journalctl -u cloude-autoupdate -f
tail -f /var/log/cloude-autoupdate.log
```

### Intervall anpassen

In `auto-update.timer` die Zeile `OnUnitActiveSec=5min` ändern (z.B. `15min`, `1h`).

---

## Plugin-System

Plugins liegen unter `plugins/installed/`. Jedes Plugin enthält eine `plugin.json` mit Metadaten.

### Plugin aktivieren

1. Plugin-Verzeichnis nach `plugins/installed/<name>/` legen
2. Im Admin-Panel unter **Plugins** aktivieren

### Eigene Plugins entwickeln

Siehe `cloudservice/plugins/example_clock_preview/` als Referenz-Implementierung.

Verfügbare Hooks:
- `UI_DASHBOARD_WIDGET` – Dashboard-Widgets
- `UI_NAVBAR_ITEM` – Navigationseinträge
- `STORAGE_FILE_UPLOAD` – Upload-Verarbeitung
- `STORAGE_FILE_DOWNLOAD` – Download-Verarbeitung

---

## Troubleshooting

### 502 Bad Gateway

```bash
sudo systemctl status gunicorn
sudo journalctl -u gunicorn -n 50
sudo systemctl restart gunicorn
```

### Static/Media Files fehlen

```bash
source /home/storage/Cloude/venv/bin/activate
cd /home/storage/Cloude/cloudservice
python manage.py collectstatic --noinput
```

### Migrations-Fehler

```bash
python manage.py migrate --fake-initial
python manage.py makemigrations
python manage.py migrate
```

### Auto-Update läuft nicht

```bash
# Service manuell testen:
sudo /usr/local/bin/cloude-auto-update.sh

# Logs prüfen:
tail -50 /var/log/cloude-autoupdate.log
journalctl -u cloude-autoupdate --no-pager
```

---

## Support

- **Issues:** [GitHub Issues](https://github.com/aboro72/Cloude/issues)
- **Entwickler:** Andreas Borowczak | [Aboro IT](https://aboro-it.de)
