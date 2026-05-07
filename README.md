# Cloude – Django Cloud Storage

Ein moderner Cloud-Speicherdienst auf Basis von Django 5, Gunicorn, Daphne und Celery.

**Entwickelt von Andreas Borowczak | [AboroSoft](https://aborosoft.com)**

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
- **Messenger** – Echtzeit-Chat mit Kanälen, Direktnachrichten, Reaktionen und Einladungslinks
- **Video-Call** – P2P-Videoanrufe direkt im DM-Fenster (Jitsi Meet, austauschbar)
- **Plugin-System** – Erweiterbar durch Hook-basierte Plugins
- **WebSocket** – Echtzeit-Benachrichtigungen über Daphne/Channels
- **REST-API** – Vollständige API mit JWT-Authentifizierung
- **Auto-Update** – Automatische Aktualisierung vom GitHub Master-Branch

---

## Projektstruktur

```
Cloude/
├── cloudservice/                       # Django-Projekt (manage.py liegt hier)
│   ├── accounts/                       # Benutzerverwaltung & Profile
│   ├── api/                            # REST-API (DRF + JWT)
│   ├── config/                         # Django-Konfiguration (settings, urls, wsgi, asgi)
│   ├── core/                           # Dashboard, WebSocket-Consumer, Navigation
│   ├── departments/                    # Abteilungsverwaltung
│   ├── jitsi/                          # Meeting-System (Jitsi-Integration)
│   ├── messenger/                      # Echtzeit-Messenger (Kanäle, DMs, Video-Calls)
│   ├── news/                           # Firmen-News (Magazin-Layout)
│   ├── plugins/                        # Plugin-System (Loader, Hooks, Admin)
│   │   ├── example_clock_preview/      # Beispiel-Plugin (Referenz)
│   │   └── example_markdown_preview/   # Beispiel-Plugin (Markdown)
│   ├── sharing/                        # Dateifreigaben & öffentliche Links
│   ├── storage/                        # Dateispeicher-Verwaltung
│   ├── templates/                      # HTML-Templates
│   ├── static/                         # CSS, JS, Bilder (Quellen)
│   ├── tests/                          # Tests
│   └── manage.py
├── django-platform-auth/               # Eigenes Authentifizierungs-Modul
│   └── platform_auth/
├── plugins/                            # Installierte Plugins & Pakete
│   ├── installed/
│   │   ├── clock_preview/              # Uhr-Widget
│   │   ├── collabora_online/           # Online-Office-Integration
│   │   ├── forms_builder/              # Formular-Builder
│   │   ├── landing_editor/             # GrapesJS Seiteneditor (Staff only)
│   │   ├── mysite_hub/                 # Persönliches Dashboard (MySite)
│   │   ├── people_directory/           # Mitarbeiterverzeichnis
│   │   ├── rss_feed/                   # RSS-Feed-Widget
│   │   ├── tasks_board/                # Kanban-Board
│   │   └── weather/                    # Wetter-Widget
│   └── packages/                       # Gezippte Plugin-Pakete
├── logs/                               # Server-Logs
├── requirements.txt                    # Python-Abhängigkeiten (Windows/Dev)
├── requirements-linux.txt              # Python-Abhängigkeiten (Linux)
├── requirements-deploy-linux.txt       # Python-Abhängigkeiten (Deploy)
├── .env.example                        # Umgebungsvariablen-Vorlage
├── gunicorn.service                    # Systemd Service (WSGI)
├── daphne.service                      # Systemd Service (ASGI/WebSocket)
├── demo-password-reset.service         # Systemd Service (Demo-Reset)
├── demo-password-reset.timer           # Systemd Timer (alle 30 Min.)
├── auto-update.service                 # Systemd Service (GitHub-Update)
├── auto-update.timer                   # Systemd Timer (alle 5 Min.)
├── auto-update.sh                      # Update-Skript
├── reset_demo_password.sh              # Demo-Passwort-Reset Skript
├── nginx.conf                          # Nginx-Konfiguration
└── nginx-proxy.conf                    # Nginx Proxy-Konfiguration
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
pip install -r requirements-linux.txt
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

### Voraussetzungen (wichtig)

- Repo liegt auf dem Server unter: `/home/storage/Cloude`
- Virtualenv liegt unter: `/home/storage/Cloude/venv`
- Django liegt unter: `/home/storage/Cloude/cloudservice/manage.py`
- GitHub Remote ist als `origin` konfiguriert (empfohlen via SSH)
- Der Server kann `git fetch/pull` ohne Passwortabfrage ausführen (Deploy Key oder PAT)
- Dienste existieren (oder werden im Skript automatisch übersprungen):
  - `gunicorn.service`, `daphne.service`, `celery.service`, `celery-beat.service`

Wenn Pfade oder Branch anders sind, passe sie in `auto-update.sh` an (`REPO_DIR`, `BRANCH`, `SERVICES`).

### GitHub → Server Zugriff (Deploy Key, empfohlen)

Auf dem Server **als `storage` User**:

```bash
sudo su - storage
ssh-keygen -t ed25519 -C "cloude-auto-update" -f ~/.ssh/cloude_autoupdate -N ""

# known_hosts füllen (einmalig)
ssh -i ~/.ssh/cloude_autoupdate -o StrictHostKeyChecking=accept-new git@github.com
```

Dann in GitHub:

- Repo → **Settings** → **Deploy keys** → **Add deploy key**
- Inhalt von `~/.ssh/cloude_autoupdate.pub` einfügen
- Empfehlung: **Read-only** (kein Write Access)

Remote auf SSH setzen (falls nötig):

```bash
cd /home/storage/Cloude
git remote set-url origin git@github.com:aboro72/Cloude.git
```

SSH Config anlegen (`/home/storage/.ssh/config`):

```sshconfig
Host github.com
  IdentityFile ~/.ssh/cloude_autoupdate
  IdentitiesOnly yes
```

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

### Optional: manuell als `storage` ausführen

Nur nötig, wenn der `storage`-User den Updater selbst starten soll (Timer läuft standardmäßig als root):

```bash
cp /home/storage/Cloude/auto-update.sudoers /etc/sudoers.d/cloude-autoupdate
chmod 440 /etc/sudoers.d/cloude-autoupdate

# Test (als storage):
sudo -u storage sudo /usr/local/bin/cloude-auto-update.sh
```

### Status & Logs prüfen

```bash
systemctl status auto-update.timer
# systemd Unit-Logs:
journalctl -u auto-update.service -n 200 --no-pager
# oder via SyslogIdentifier (aus der Service-Datei):
journalctl -t cloude-autoupdate -n 200 --no-pager
tail -f /var/log/cloude-autoupdate.log
```

### Intervall anpassen

In `auto-update.timer` die Zeile `OnUnitActiveSec=5min` ändern (z.B. `15min`, `1h`).

---

## Messenger

Der Messenger ist workspace-basiert und an das Firmenprofil (`Company`) geknüpft. Jede Firma hat einen eigenen Namespace über den `workspace_key`.

### Funktionen

| Feature | Beschreibung |
|---|---|
| Kanäle | Öffentliche und private Gruppenräume |
| Direktnachrichten | 1:1-Chat zwischen Workspace-Mitgliedern |
| Reaktionen | Emoji-Reaktionen auf Nachrichten |
| Antworten | Thread-ähnliche Antworten auf einzelne Nachrichten |
| Einladungslinks | Temporäre Links mit Nutzungslimit und Ablaufdatum |
| Präsenz | Online/Offline-Status via WebSocket |
| Video-Call | Integrierter Videoanruf direkt im DM-Fenster |

### URL-Schema

```
/<workspace_key>/messenger/                        # Übersicht
/<workspace_key>/messenger/channel/<slug>/         # Kanal-/Gruppenraum
/<workspace_key>/messenger/dm/<username>/          # Direktnachricht öffnen/erstellen
/<workspace_key>/messenger/channel/create/         # Neuen Kanal anlegen
/messenger/invite/<token>/                         # Einladungslink einlösen
```

### Video-Call (Jitsi) in DM-Räumen

Video-Calls sind in DM-Räumen über den "Video-Call"-Button im Header verfügbar. Die Integration nutzt aktuell `meet.jit.si` als öffentlichen Server.

**Auf eigene Jitsi-Instanz umziehen:**

In `templates/messenger/messenger.html` eine Zeile ändern:

```javascript
// vorher:
jitsiApi = new JitsiMeetExternalAPI('meet.jit.si', { ... });

// nachher:
jitsiApi = new JitsiMeetExternalAPI('jitsi.deine-domain.de', { ... });
```

Selbst gehostete Jitsi-Instanz aufsetzen (Docker):

```bash
git clone https://github.com/jitsi/docker-jitsi-meet
cd docker-jitsi-meet
cp env.example .env
# .env anpassen (PUBLIC_URL, Passwörter etc.)
docker compose up -d
```

---

## Meetings (Jitsi)

Geplante und spontane Video-Meetings, workspace-gebunden an das `Company`-Modell.
Konfiguration über `.env`: `JITSI_URL`, `JITSI_APP_ID`, `JITSI_APP_SECRET`.

### Features

| Feature | Beschreibung |
|---|---|
| Meeting planen | Titel, Beschreibung, Start/Ende, Eingeladene auswählen |
| Raum erst beim Start | Jitsi-Raumname wird erst generiert wenn "Starten" geklickt wird |
| Meeting-Seite | Eingebetteter Jitsi-Call, kein Tab-Wechsel nötig |
| Nach Meeting → MySite | Nach Verlassen oder Auflegen automatischer Redirect zur MySite |
| MySite-Widget | Laufende & geplante Meetings direkt auf der MySite sichtbar |
| API | Vollständige REST-API für externe Clients (siehe unten) |

### URL-Schema

```
/meetings/                        # Übersicht: laufend / geplant / vergangen
/meetings/schedule/               # POST: Meeting anlegen
/meetings/<id>/start/             # POST: Meeting starten (Raum wird erstellt)
/meetings/<id>/join/              # GET: laufendem Meeting beitreten → Room-Seite
/meetings/<id>/room/              # Meeting-Room mit eingebettetem Jitsi
/meetings/<id>/end/               # POST: Meeting beenden
/meetings/<id>/cancel/            # POST: Meeting absagen
```

### Meeting-Lebenszyklus

```
planned → (start) → running → (end) → ended
planned → (cancel) → cancelled
```

Der Jitsi-Raumname (`room_name`) bleibt leer bis `start()` aufgerufen wird.
Erst dann wird ein deterministischer Slug aus Titel + UUID-Suffix generiert.

### MySite-Widget

Das Widget `"Meine Meetings"` erscheint auf der MySite automatisch,
sobald mindestens ein laufendes oder geplantes Meeting für den Nutzer existiert.
Eingebaut in `plugins/installed/mysite_hub/providers.py` (`_build_upcoming_meetings`).

---

## REST-API

Basis-URL: `/api/`
Authentifizierung: JWT (`/api/auth/token/`)
Dokumentation: `/api/docs/` (Swagger) · `/api/redoc/`

### Endpunkte-Übersicht

| Ressource | Pfad | Methoden |
|---|---|---|
| Dateien | `/api/files/` | GET, POST, PATCH, DELETE |
| Ordner | `/api/folders/` | GET, POST, PATCH, DELETE |
| Freigaben | `/api/shares/` | GET, POST, PATCH, DELETE |
| Public Links | `/api/public-links/` | GET, POST, PATCH, DELETE |
| Suche | `/api/search/?q=` | GET |
| Storage-Quota | `/api/storage/quota/` | GET |
| Benachrichtigungen | `/api/notifications/` | GET |
| Abteilungen | `/api/departments/` | GET |
| Team Sites | `/api/team-sites/` | GET |
| Kanban-Boards | `/api/boards/` | GET |
| Tasks | `/api/tasks/` | GET |
| News-Kategorien | `/api/news/categories/` | GET |
| News-Artikel | `/api/news/articles/` | GET |
| **Meetings** | `/api/meetings/` | GET, POST, PATCH, DELETE |
| Messenger-Räume | `/api/messenger/rooms/` | GET, POST |
| Nachrichten | `/api/messenger/rooms/{id}/messages/` | GET, POST, PATCH, DELETE |
| Direktnachricht | `/api/messenger/direct/` | POST |
| Chat-Einladungen | `/api/messenger/invites/{token}/` | GET |

### Meeting-API im Detail

```
GET    /api/meetings/                    # eigene Meetings (Organisator oder Eingeladener)
GET    /api/meetings/?status=planned     # nach Status filtern (planned/running/ended/cancelled)
POST   /api/meetings/                    # Meeting planen
GET    /api/meetings/{id}/               # Meeting-Details
PATCH  /api/meetings/{id}/               # Titel/Beschreibung/Zeiten ändern
DELETE /api/meetings/{id}/               # Meeting löschen
POST   /api/meetings/{id}/start/         # Meeting starten
POST   /api/meetings/{id}/end/           # Meeting beenden
POST   /api/meetings/{id}/cancel/        # Meeting absagen
GET    /api/meetings/{id}/join_url/      # Jitsi-JWT + Join-URL abrufen (nur running)
```

**Beispiel – Meeting planen:**

```json
POST /api/meetings/
{
  "title": "Wöchentliches Standup",
  "description": "15-Minuten-Update",
  "scheduled_start": "2026-05-10T09:00:00",
  "scheduled_end":   "2026-05-10T09:15:00",
  "invitee_ids": [3, 7, 12]
}
```

**Beispiel – Join-URL abrufen:**

```json
GET /api/meetings/42/join_url/
→ {
    "token": "eyJ...",
    "url": "https://meet.aborosoft.com/standup-a1b2c3?jwt=eyJ...",
    "room_name": "standup-a1b2c3"
  }
```

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
- **Entwickler:** Andreas Borowczak | [AboroSoft](https://aborosoft.com)
