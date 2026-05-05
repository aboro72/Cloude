# CloudService

Eine selbst gehostete Intranet-Plattform als SharePoint-Alternative. Plugin-basiert, schlank und auf Django 5.x aufgebaut.

**Entwickelt von Andreas Borowczak | [Aboro IT](https://aboro-it.de)**

---

## Inhaltsverzeichnis

- [Überblick](#überblick)
- [Tech Stack](#tech-stack)
- [Schnellstart](#schnellstart)
- [Projektstruktur](#projektstruktur)
- [Kernmodule](#kernmodule)
- [Plugin-System](#plugin-system)
- [Installierte Plugins](#installierte-plugins)
- [URL-Struktur](#url-struktur)
- [Konfiguration (.env)](#konfiguration-env)
- [Datenbank](#datenbank)
- [WebSocket / Echtzeit](#websocket--echtzeit)
- [REST API](#rest-api)
- [Mehrsprachigkeit](#mehrsprachigkeit)
- [Sicherheit](#sicherheit)
- [Server-Deployment (Linux)](#server-deployment-linux)
- [Auto-Update (GitHub → Server)](#auto-update-github--server)
- [Entwicklung](#entwicklung)
- [Troubleshooting](#troubleshooting)

---

## Überblick

CloudService ist eine Django-basierte Intranet-Plattform, die SharePoint-typische Funktionen vereint: Dateispeicherung, Team-Sites, Unternehmens-News, Echtzeit-Messenger, persönliche Dashboards und einen visuellen Page-Builder — ohne die Komplexität und Kosten kommerzieller Lösungen.

**Kernprinzipien:**
- Selbst gehostet, vollständige Datenkontrolle
- Plugin-basiert — Funktionen lassen sich ein- und ausschalten
- Schlankes Design mit Bootstrap 5.3 und Bootstrap Icons
- Deutsche Benutzeroberfläche, mehrsprachig vorbereitet (DE / EN / FR)

---

## Tech Stack

| Bereich | Technologie |
|---|---|
| Backend | Django 5.x, Python 3.10+ |
| Datenbank | SQLite (Dev), MySQL, PostgreSQL (Prod) |
| Optional NoSQL | MongoDB 4.x (deaktivierbar per .env) |
| WebSocket | Django Channels + Daphne (ASGI) |
| Cache / Broker | Redis (Prod), InMemory (Dev) |
| Task Queue | Celery + django-celery-beat |
| Frontend | Bootstrap 5.3, Bootstrap Icons 1.11 |
| Page Builder | GrapesJS 0.21.13 (CDN) |
| Drag & Drop | SortableJS 1.15.0 (CDN) |
| Office-Vorschau | Collabora Online (WOPI) |
| REST API | Django REST Framework + JWT |
| API-Schema | drf-spectacular (OpenAPI 3) |
| Admin | Jazzmin (erweitertes Django Admin) |
| Permissions | django-guardian (Object-Level) |
| Logging | structlog + python-json-logger + Sentry (optional) |
| Static Files | WhiteNoise (Produktion) |
| i18n | django-modeltranslation |

---

## Schnellstart

```bash
# Repository klonen
git clone https://github.com/aboro72/Cloude.git
cd Cloude

# Virtuelle Umgebung
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# .env anlegen
cp .env.example cloudservice/.env
# .env anpassen (zumindest SECRET_KEY setzen)

# Datenbankmigrationen
cd cloudservice
python manage.py migrate

# Superuser anlegen
python manage.py createsuperuser

# Demo-Benutzer erstellen (optional)
python manage.py create_demo_users

# Abteilungsgruppen einrichten (optional)
python manage.py setup_groups

# Entwicklungsserver starten
python manage.py runserver
```

Die Anwendung ist dann unter `http://localhost:8000` erreichbar.

---

## Projektstruktur

```
Cloude/
├── cloudservice/               # Django-Projektwurzel (manage.py)
│   ├── config/                 # settings.py, urls.py, asgi.py, wsgi.py
│   ├── core/                   # Dateispeicherung, Ordner, Benachrichtigungen, Aktivitätslog
│   ├── accounts/               # Benutzerprofile, Firmen, Sitzungen, 2FA, Audit-Log
│   ├── storage/                # Speicher-Views und -Logik
│   ├── sharing/                # Dateifreigabe, Team-Sites, öffentliche Links
│   ├── news/                   # Unternehmens-News (Magazin-Layout)
│   ├── departments/            # Abteilungen und Mitgliedschaften
│   ├── messenger/              # Echtzeit-Chat, Kanäle, Direktnachrichten
│   ├── api/                    # REST API (DRF + JWT)
│   ├── plugins/                # Plugin-Engine (Hooks, Loader, UI-Registry)
│   ├── templates/              # Globale Templates
│   ├── static/                 # Globale statische Dateien
│   └── locale/                 # Übersetzungsdateien (DE/EN/FR)
├── plugins/
│   └── installed/              # Installierte Plugins (jedes = eigene Django-App)
│       ├── clock_preview/
│       ├── collabora_online/
│       ├── forms_builder/
│       ├── landing_editor/
│       ├── mysite_hub/
│       ├── people_directory/
│       ├── rss_feed/
│       ├── tasks_board/
│       └── weather/
├── media/                      # Benutzer-Uploads (Avatare, Dateien, etc.)
├── logs/                       # Rotating Log-Dateien
├── requirements.txt
├── .env.example
├── gunicorn.service            # Systemd Service (WSGI)
├── daphne.service              # Systemd Service (ASGI/WebSocket)
├── auto-update.sh              # Automatisches Update-Skript
├── auto-update.service         # Systemd Service für Auto-Update
├── auto-update.timer           # Systemd Timer (alle 5 Minuten)
├── nginx.conf                  # Nginx-Konfiguration
└── db.sqlite3                  # SQLite-Datenbank (Dev)
```

---

## Kernmodule

### Dateispeicherung (`core`)
- `StorageFolder` — verschachtelte Ordnerstruktur pro Benutzer
- `StorageFile` — Dateien mit SHA256-Hash, MIME-Typ, Versionszähler, Download-Zähler
- `FileVersion` — vollständige Versionsverwaltung mit Wiederherstellung
- Papierkorb-Funktion (Soft Delete mit `is_trashed`, `trashed_at`, `original_folder`)
- Automatische SHA256-Hashberechnung und MIME-Erkennung beim Speichern
- Firmenbezogener Speicherpfad: `companies/<workspace_key>/users/<username>/files/`
- `ActivityLog` — vollständiger Audit-Trail aller Dateioperationen (Upload, Download, Umbenennen, Verschieben, Freigabe)
- `Notification` — Benutzernachrichten (Freigabe, News, Kommentare, @Mentions, Team-News, Speicherlimit)
- Management-Command: `cleanup_trash` (Papierkorb automatisch leeren)

### Benutzerverwaltung (`accounts`)
- `Company` — Firmen-Workspaces mit Branding (Logo, Hero-Bild/-Video, Primär-/Sekundärfarbe, Custom HTML/CSS)
- `UserProfile` — erweitertes Profil mit:
  - Speicherkontingent (Standard: 5 GB) mit Nutzungsberechnung, Warnschwelle und Vollprüfung
  - Farbpaletten (Default, Forest, Sunset, Berry, Slate, Custom)
  - Design-Varianten (Gradient, Minimal, Contrast)
  - Hell-/Dunkel-/Auto-Theme
  - MySite-Hero (Gradient / Bild / Video)
  - Mitarbeiterverzeichnis-Felder (Jobtitel, Abteilung, Standort, Vorgesetzter)
- `UserSession` — Sitzungsverfolgung mit IP, User-Agent, Gerät und Ablaufzeit
- `TwoFactorAuth` — TOTP / SMS / E-Mail (vorbereitet)
- `AuditLog` — Login, Logout, Passwortänderungen, 2FA, Berechtigungsänderungen
- `PasswordReset` — sichere Reset-Tokens (UUID) mit Ablaufdatum
- Management-Commands: `create_demo_users`, `reset_demo_password`

### Team-Sites & Freigabe (`sharing`)
- `GroupShare` — Team-Sites mit Hintergrundbild/-video, Abteilungsbezug, Team-Leitern, Objekt-Level-Permissions
- `UserShare` — Direkte Benutzer-zu-Benutzer-Freigabe mit granularen Berechtigungen (view / download / edit / delete / share / admin)
- `PublicLink` — Öffentliche Links mit optionalem Passwortschutz (PBKDF2), Ablaufdatum und Download-Limit, View-/Download-Zähler
- `TeamSiteNews` — News-Beiträge pro Team-Site mit Tags, View-Zähler, Pin-Funktion, Kommentaren und Reaktionen
- `ShareLog` — Protokoll aller Freigabeaktivitäten
- Objekt-Level-Permissions via `django-guardian`

### Unternehmens-News (`news`)
- `NewsCategory` — Kategorien mit Farbe und Bootstrap Icon
- `NewsArticle` — Artikel mit Cover-Bild, Tags, Featured-/Pinned-/Published-Flag, geplanter Veröffentlichung, View-Zähler
- Magazin-Layout unter `/news/`
- `Comment` — threaded Kommentare via GenericFK (für News und Team-Site-News nutzbar)
- `Reaction` — Like / Heart-Reaktionen via GenericFK
- AJAX-Reaktionen und Kommentare ohne Seitenreload

### Abteilungen (`departments`)
- `Department` — Abteilungen mit Bootstrap Icon, Farbe, Abteilungsleiter
- `DepartmentMembership` — Mitgliedschaft mit Rollen (Mitglied / Manager / Abteilungsleiter)
- Verknüpfung mit Team-Sites (`GroupShare.department`)
- Custom Permissions: `create_department`, `manage_any_department`
- Management-Command: `setup_groups`

### Messenger (`messenger`)
- `ChatRoom` — Kanäle, Direktnachrichten und Gruppen-Chats; firmenübergreifend via Guest Companies
- `ChatMembership` — Mitgliedschaft mit Rollen (Owner / Admin / Member), Mute-Funktion, Ungelesen-Zähler
- `ChatMessage` — Text, Dateianhänge aus dem Speicher, Antworten (Reply-to), Emoji-Reaktionen (JSON), Soft Delete
- `ChatInvite` — Einladungslinks mit Ablaufdatum und Nutzungslimit (firmenübergreifend)
- WebSocket-Echtzeit-Übertragung via Django Channels
- Video-Conferencing-Felder vorbereitet (Jitsi / Daily / Whereby)

---

## Plugin-System

Plugins sind eigenständige Django-Apps unter `plugins/installed/<name>/`. Jedes Plugin hat eine `plugin.json` und eine Standard-Django-`AppConfig`.

### Hooks

| Hook | Zweck |
|---|---|
| `UI_MENU_ITEM` | Navigationseintrag in der Seitenleiste |
| `UI_APP_PAGE` | Eigene Seite unter `/core/apps/<slug>/` |
| `file_preview_provider` | Eigener Dateivorschau-Handler |

Hooks werden in `AppConfig.ready()` registriert. Der Plugin-Template-Loader (`plugins.template_loader.PluginTemplateLoader`) findet Plugin-Templates automatisch.

### Plugin-Einstellungen
- Plugins werden über `Plugin.settings` (JSONField in der Datenbank) konfiguriert
- `Plugin.position` steuert die Anzeigereihenfolge in der Navigation
- Management-Commands: `package_plugins`, `test_plugin_hotload`

---

## Installierte Plugins

| Plugin | Slug | Beschreibung |
|---|---|---|
| `landing_editor` | `landing-editor` | Visueller Page-Builder (GrapesJS) für Landing-Page, Impressum und MySite-Widget-Reihenfolge. 30+ Bootstrap-5-Blöcke. Nur für Staff. |
| `mysite_hub` | `mysite` | Persönliches Dashboard (SharePoint MySite-Stil). Widgets: News, Kürzliche Dateien, Team-News, Abteilungsseiten, Aktivitäten. Drag-&-Drop via SortableJS. |
| `tasks_board` | `tasks` | Persönliches und Team-Kanban-Board mit Drag-and-Drop. |
| `forms_builder` | `forms` | Drag-Drop Formular-Builder für Umfragen und IT-Anfragen. |
| `people_directory` | `people` | Mitarbeiterverzeichnis mit Suche, Abteilungsfilter und Organigramm. |
| `collabora_online` | `collabora-online` | Office-Dokumente direkt im Browser bearbeiten und anzeigen (Collabora Online via WOPI). Unterstützt .docx, .xlsx, .pptx. |
| `rss_feed` | — | RSS-Feed-Widget für das Dashboard. |
| `weather` | — | Wetter-Widget für das Dashboard. |
| `clock_preview` | — | Uhr-Widget für das Dashboard. |

### Landing Editor — Datenformat

Der Landing Editor speichert alle Einstellungen in `Plugin.settings`:

```json
{
  "pages": {
    "landing":   { "html": "...", "css": "..." },
    "impressum": { "html": "...", "css": "..." }
  },
  "mysite_widgets": [
    { "id": "news",      "label": "Neuigkeiten",       "icon": "bi-newspaper",    "visible": true },
    { "id": "files",     "label": "Kürzliche Dateien", "icon": "bi-folder2-open", "visible": true },
    { "id": "team_news", "label": "Team News",          "icon": "bi-people-fill",  "visible": true },
    { "id": "teams",     "label": "Abteilungsseiten",   "icon": "bi-building",     "visible": true },
    { "id": "activity",  "label": "Aktivitäten",        "icon": "bi-activity",     "visible": false }
  ],
  "color_primary": "#667eea",
  "color_secondary": "#764ba2"
}
```

Tastenkürzel im Builder: `Ctrl+S` speichert, Geräte-Toggle (Desktop / Tablet / Mobil), Undo/Redo.

---

## URL-Struktur

| URL | Beschreibung | Zugriffsrecht |
|---|---|---|
| `/` | Startseite (Landing Page oder MySite Hub) | öffentlich / eingeloggt |
| `/accounts/login/` | Anmeldung | öffentlich |
| `/core/impressum/` | Impressum | öffentlich |
| `/news/` | Unternehmens-News (Magazin) | eingeloggt |
| `/news/<slug>/` | Artikel-Detailseite | eingeloggt |
| `/sharing/` | Team-Sites & Freigaben | eingeloggt |
| `/storage/` | Dateispeicher | eingeloggt |
| `/core/apps/<slug>/` | Plugin-Seiten | eingeloggt |
| `/landing-editor/save/` | AJAX-Speicherung (Page Builder) | Staff |
| `/api/` | REST API | JWT / Session |
| `/api/schema/` | OpenAPI 3 Schema | Staff |
| `/api/docs/` | Swagger UI | Staff |
| `/admin/` | Django Admin (Jazzmin) | Staff |

---

## Konfiguration (.env)

Alle Einstellungen werden via `python-decouple` aus `cloudservice/.env` geladen.

```ini
# Pflicht in Produktion
SECRET_KEY=dein-geheimer-schluessel
DEBUG=False
ALLOWED_HOSTS=meine-domain.de,www.meine-domain.de

# Datenbank (sqlite / mysql / postgresql)
DB_ENGINE=postgresql
DB_NAME=cloudservice
DB_USER=csuser
DB_PASSWORD=geheim
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/2

# Collabora Online (WOPI)
COLLABORA_BASE_URL=https://office.beispiel.com
CLOUDSERVICE_EXTERNAL_URL=https://cloudservice.beispiel.com
COLLABORA_ACCESS_TOKEN_TTL=3600

# MongoDB (optional, Standard: deaktiviert)
MONGODB_ENABLED=False
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB=appdb

# CORS
CORS_ALLOWED_ORIGINS=https://meine-domain.de

# Sentry (optional)
SENTRY_DSN=

# HTTPS (Produktion)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

## Datenbank

CloudService unterstützt drei Datenbank-Backends:

| Backend | Empfehlung |
|---|---|
| **SQLite** | Entwicklung und kleine Installationen |
| **MySQL** | Mittlere Produktionsumgebungen |
| **PostgreSQL** | Empfohlen für Produktion |

```bash
cd cloudservice
python manage.py migrate
```

**MongoDB** ist optional und wird für analytische oder Log-Daten eingesetzt. Wenn `MONGODB_ENABLED=False` gesetzt ist (Standard), läuft die App vollständig ohne MongoDB.

---

## WebSocket / Echtzeit

Der Messenger nutzt Django Channels mit ASGI (Daphne).

- **Entwicklung:** InMemoryChannelLayer (kein Redis nötig)
- **Produktion:** RedisChannelLayer

ASGI-Anwendung starten (Produktion):

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

## REST API

Die REST API basiert auf Django REST Framework mit JWT-Authentifizierung.

- **Basis-URL:** `/api/`
- **Schema (OpenAPI 3):** `/api/schema/`
- **Swagger UI:** `/api/docs/`
- **Authentifizierung:** Bearer Token (JWT) oder Session

Token anfordern:

```bash
curl -X POST /api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "passwort"}'
```

Rate-Limits: anonyme Anfragen 100/Stunde, authentifiziert 1000/Stunde.
Token-Gültigkeit: Access Token 1 Stunde, Refresh Token 7 Tage.

---

## Mehrsprachigkeit

| Sprache | Code |
|---|---|
| Deutsch (Standard) | `de` |
| Englisch | `en` |
| Französisch | `fr` |

Zeitzone: `Europe/Berlin`. Übersetzungen unter `cloudservice/locale/`.

```bash
python manage.py makemessages -l en -l fr
python manage.py compilemessages
```

---

## Sicherheit

- Objekt-Level-Berechtigungen via `django-guardian`
- CSRF-Schutz aktiviert (SameSite=Lax)
- Password-Validierung (Mindestlänge, Häufigkeit, Ähnlichkeit)
- SHA256-Datei-Hashing zur Integritätsprüfung
- Öffentliche Links: optionaler Passwortschutz (PBKDF2-Hash)
- Passwort-Reset-Tokens mit Ablaufdatum (UUID)
- Zwei-Faktor-Authentifizierung vorbereitet (TOTP / SMS / E-Mail)
- Audit-Log für alle sicherheitsrelevanten Aktionen
- Sentry-Integration für Fehler-Monitoring (optional)
- WhiteNoise für sichere Auslieferung statischer Dateien in Produktion
- Reverse-Proxy-kompatibel (`SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`)
- Custom Permissions: `create_groupshare`, `manage_any_groupshare`, `create_department`, `manage_any_department`

---

## Server-Deployment (Linux)

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

### 3. Datenbank & statische Dateien

```bash
cd cloudservice
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py setup_groups
```

### 4. Systemd Services einrichten

```bash
# Als root:
sudo cp /home/storage/Cloude/gunicorn.service /etc/systemd/system/
sudo cp /home/storage/Cloude/daphne.service   /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn daphne
```

### 5. Nginx konfigurieren

```bash
sudo cp /home/storage/Cloude/nginx.conf /etc/nginx/sites-available/cloude
sudo ln -s /etc/nginx/sites-available/cloude /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Auto-Update (GitHub → Server)

Das Auto-Update-System prüft alle **5 Minuten**, ob neue Commits im `master`-Branch vorliegen, und aktualisiert den Server automatisch.

### Was passiert bei einem Update

1. `git fetch origin master` — neuen Stand prüfen
2. Vergleich `HEAD` vs. `origin/master` — kein Pull wenn nichts Neues
3. `git pull` — Änderungen einspielen
4. `pip install -r requirements.txt` — neue Abhängigkeiten installieren
5. `manage.py migrate` — Datenbankmigrationen ausführen
6. `manage.py collectstatic` — statische Dateien aktualisieren
7. Dienste neu starten (gunicorn, daphne, celery, celery-beat)

### Installation

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

### Status & Logs

```bash
systemctl status auto-update.timer
journalctl -u cloude-autoupdate -f
tail -f /var/log/cloude-autoupdate.log
```

---

## Entwicklung

### Nützliche Management-Commands

```bash
# Demo-Benutzer anlegen
python manage.py create_demo_users

# Demo-Passwort zurücksetzen
python manage.py reset_demo_password

# Abteilungsgruppen und Berechtigungen einrichten
python manage.py setup_groups

# Papierkorb leeren (für Cron/Celery)
python manage.py cleanup_trash

# Plugin als Paket exportieren
python manage.py package_plugins

# Plugin-Hotload testen
python manage.py test_plugin_hotload
```

### Celery (Task-Queue)

```bash
# Worker starten
celery -A config worker -l info

# Beat-Scheduler starten (geplante Tasks)
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Logs

Log-Dateien werden unter `logs/cloudservice.log` gespeichert (rotierend, max. 10 MB, 10 Backups).

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
