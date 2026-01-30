# CloudService - Nextcloud-ähnlicher Cloud-Service mit Django 5.x

Ein vollständig funktionsfähiger Cloud-Service ähnlich Nextcloud, entwickelt mit Django 5.x, Python 3.10+ und modernen Frontend-Technologien.

## 🎯 Features

### Dateiverwaltung
- ✅ Datei-Upload/Download mit Drag & Drop
- ✅ Ordnerstruktur erstellen und verwalten
- ✅ Dateien/Ordner umbenennen, verschieben, löschen
- ✅ Dateiversioning mit Wiederherstellungsoption
- ✅ Dateityp-Erkennung und Icons
- ✅ Soft-Delete (Papierkorb) mit Ablaufzeit

### Benutzer- und Rechteverwaltung
- ✅ Benutzerregistrierung und Authentifizierung (JWT + Session)
- ✅ Rollenbasierte Zugriffskontrolle (Admin, User, Moderator)
- ✅ Benutzerprofilverwaltung
- ✅ Speicherplatz-Quotas pro Benutzer
- ✅ Zwei-Faktor-Authentifizierung
- ✅ Session-Management

### Sharing und Kollaboration
- ✅ Dateien/Ordner mit anderen Benutzern teilen
- ✅ Öffentliche Links mit Passwort-Schutz
- ✅ Berechtigungen (Lesen/Schreiben) für geteilte Inhalte
- ✅ Ablaufzeiten für geteilte Links
- ✅ Gruppen-Sharing
- ✅ Audit-Logging von Share-Aktivitäten

### Web-Interface
- ✅ Responsive Dashboard
- ✅ Drag & Drop Upload
- ✅ Datei-Preview für gängige Formate
- ✅ Kontextmenüs für Dateioperationen
- ✅ Such- und Filterfunktionen
- ✅ Dark Mode Support

### API
- ✅ REST API mit Django REST Framework
- ✅ OpenAPI/Swagger Dokumentation
- ✅ JWT Authentication
- ✅ Rate Limiting
- ✅ Pagination und Filtering

### Erweiterte Features
- ✅ WebSocket-Unterstützung für Real-time Updates
- ✅ Celery für asynchrone Tasks
- ✅ Redis für Caching
- ✅ Monitoring und Logging
- ✅ Mehrsprachigkeitsunterstützung (Deutsch, Englisch, Französisch)
- ✅ Activity Logging und Audit Trail

## 🏗️ Architektur

```
CloudService/
├── cloudservice/              # Django Projekt
│   ├── config/               # Projektkonfiguration
│   │   ├── settings.py       # Django Settings
│   │   ├── urls.py          # URL-Routing
│   │   ├── wsgi.py          # WSGI Server
│   │   ├── asgi.py          # ASGI Server (WebSocket)
│   │   └── __init__.py
│   ├── core/                 # Kern-App (Dateiverwaltung)
│   │   ├── models.py        # StorageFile, StorageFolder, FileVersion
│   │   ├── views.py         # Views für Dashboard
│   │   ├── urls.py          # URLs
│   │   ├── signals.py       # Django Signals
│   │   ├── consumers.py     # WebSocket Consumer
│   │   └── routing.py       # WebSocket Routing
│   ├── accounts/             # Benutzer-Management
│   │   ├── models.py        # UserProfile, UserSession, TwoFactorAuth
│   │   ├── views.py         # Auth Views
│   │   ├── urls.py          # URLs
│   │   └── signals.py       # Signals
│   ├── storage/              # Speicherverwaltung
│   │   ├── models.py        # StorageStats, StorageBackup, TrashBin
│   │   ├── views.py         # Storage Views
│   │   └── urls.py          # URLs
│   ├── sharing/              # Sharing & Permissions
│   │   ├── models.py        # UserShare, PublicLink, Permission
│   │   ├── views.py         # Sharing Views
│   │   └── urls.py          # URLs
│   ├── api/                  # REST API
│   │   ├── serializers.py   # DRF Serializers
│   │   ├── views.py         # API ViewSets
│   │   ├── permissions.py   # Custom Permissions
│   │   └── urls.py          # API URLs
│   ├── templates/            # HTML Templates
│   ├── static/              # CSS, JavaScript, Images
│   └── manage.py
├── Dockerfile               # Docker Image
├── docker-compose.yml       # Docker Compose Stack
├── nginx.conf              # Nginx Configuration
├── requirements.txt        # Python Dependencies
├── .env.example           # Environment Variables Template
├── .gitignore            # Git Ignore Rules
└── README.md             # This file
```

## 🚀 Installation

### Voraussetzungen
- Docker & Docker Compose
- Python 3.10+
- PostgreSQL 14+
- Redis 7+

### Schnelleinstieg mit Docker

```bash
# 1. Repository klonen
git clone https://github.com/yourusername/cloudservice.git
cd cloudservice

# 2. Environment-Datei erstellen
cp .env.example .env
# Editieren Sie .env und setzen Sie Ihre Werte

# 3. Docker Compose starten
docker-compose up -d

# 4. Migrationen durchführen
docker-compose exec web python manage.py migrate

# 5. Superuser erstellen
docker-compose exec web python manage.py createsuperuser

# 6. Statische Dateien sammeln
docker-compose exec web python manage.py collectstatic --noinput
```

### Lokale Entwicklung

```bash
# 1. Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows

# 2. Dependencies installieren
pip install -r requirements.txt

# 3. Environment-Datei konfigurieren
cp .env.example .env
# Bearbeiten Sie .env für lokale Entwicklung

# 4. Datenbank-Migrationen
python cloudservice/manage.py migrate

# 5. Superuser erstellen
python cloudservice/manage.py createsuperuser

# 6. Development Server starten
python cloudservice/manage.py runserver

# 7. Redis starten (separates Terminal)
redis-server

# 8. Celery Worker starten (separates Terminal)
celery -A config worker --loglevel=info
```

## 📖 API-Dokumentation

Die API-Dokumentation ist nach dem Start unter folgenden URLs verfügbar:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Schema (OpenAPI)**: http://localhost:8000/api/schema/

### Authentifizierung

```bash
# Token erhalten
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# API aufrufen mit Token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/files/
```

## 🔒 Sicherheitsmaßnahmen

- **CSRF-Schutz**: Django CSRF Middleware
- **XSS-Schutz**: Content Security Policy Header
- **SQL-Injection**: Django ORM parametrisierte Queries
- **Sichere Datei-Uploads**: Validierung und Sandbox
- **JWT Authentication**: mit Refresh Token
- **Passwort-Hashing**: PBKDF2 mit SHA256
- **Rate Limiting**: Pro Endpoint konfigurierbar
- **CORS**: Konfigurierbar für sichere Cross-Domain Requests

## 📦 Technologie-Stack

### Backend
- **Django 5.1.4** - Web Framework
- **Django REST Framework 3.14** - REST API
- **Celery 5.4** - Task Queue
- **Channels 4.1** - WebSocket Support
- **PostgreSQL 16** - Database
- **Redis 7** - Cache & Message Broker

### Frontend
- **Bootstrap 5** - CSS Framework
- **Tailwind CSS 3** - Utility-first CSS
- **ES6+ JavaScript** - Frontend Logic
- **Fetch API** - HTTP Requests
- **WebSocket** - Real-time Updates

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Orchestration
- **Nginx** - Reverse Proxy
- **Gunicorn** - WSGI Server
- **Daphne** - ASGI Server

## 🔧 Konfiguration

### Django Settings
Siehe `cloudservice/config/settings.py` für alle Konfigurationsoptionen:

```python
# DEBUG Mode
DEBUG = True

# Erlaubte Hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Datenbank
DATABASES = {...}

# Redis/Cache
CACHES = {...}

# Datei-Upload
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
```

### Umgebungsvariablen
Bearbeiten Sie `.env`:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=cloudservice
DB_USER=postgres
DB_PASSWORD=password
REDIS_URL=redis://localhost:6379/0
```

## 📊 Datenbank-Models

### Core Models
- **StorageFile**: Dateien mit Metadaten
- **StorageFolder**: Ordnerstruktur
- **FileVersion**: Versionsverlauf
- **ActivityLog**: Aktivitätsprotokoll
- **Notification**: Benachrichtigungen

### Account Models
- **UserProfile**: Benutzerprofil mit Quotas
- **UserSession**: Session-Management
- **TwoFactorAuth**: 2FA-Einstellungen
- **AuditLog**: Audit Trail

### Sharing Models
- **UserShare**: Benutzer-zu-Benutzer Sharing
- **PublicLink**: Öffentliche Links
- **Permission**: Granulare Permissions
- **GroupShare**: Gruppen-Sharing

### Storage Models
- **StorageStats**: Statistik-Cache
- **StorageBackup**: Backup-Tracking
- **TrashBin**: Soft-Delete
- **StorageQuotaAlert**: Quota-Warnungen

## 🧪 Testing

```bash
# Tests ausführen
python manage.py test

# Mit Coverage
pytest --cov=cloudservice tests/

# Specific Test
pytest tests/test_models.py::TestStorageFile
```

## 📈 Performance

### Optimierungen
- Database Query Optimization mit `select_related` und `prefetch_related`
- Caching mit Redis
- Pagination für große Datensätze
- Asynchrone Tasks mit Celery
- Gzip Compression in Nginx
- Static Files Minification

### Monitoring
- Django Debug Toolbar (Entwicklung)
- Sentry Integration (optional)
- Logging zu Datei und Console
- Activity Logging

## 🌍 Deployment

### Production Checklist
```bash
# 1. Environment setzen
DEBUG=False
SECRET_KEY=<generate-secure-key>
ALLOWED_HOSTS=yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# 2. Database backups
pg_dump -U postgres -d cloudservice > backup.sql

# 3. Static files
python manage.py collectstatic

# 4. SSL-Zertifikate
# Siehe nginx.conf für SSL-Konfiguration

# 5. Health Check
curl http://localhost:8000/health/
```

## 📝 API Endpoints

### Dateien
```
GET    /api/files/                 - Liste Dateien
POST   /api/files/                 - Upload Datei
GET    /api/files/{id}/            - Datei-Details
PATCH  /api/files/{id}/            - Aktualisiere Datei
DELETE /api/files/{id}/            - Lösche Datei
POST   /api/files/{id}/download/   - Download Datei
POST   /api/files/{id}/star/       - Markiere als favorit
```

### Ordner
```
GET    /api/folders/               - Liste Ordner
POST   /api/folders/               - Erstelle Ordner
GET    /api/folders/{id}/          - Ordner-Details
PATCH  /api/folders/{id}/          - Aktualisiere Ordner
DELETE /api/folders/{id}/          - Lösche Ordner
GET    /api/folders/{id}/contents/ - Ordner-Inhalte
```

### Sharing
```
GET    /api/shares/                - Meine Shares
POST   /api/shares/                - Teile Datei
PATCH  /api/shares/{id}/           - Update Share
DELETE /api/shares/{id}/           - Lösche Share

GET    /api/public-links/          - Meine öffentlichen Links
POST   /api/public-links/          - Erstelle öffentlichen Link
PATCH  /api/public-links/{id}/     - Update Link
DELETE /api/public-links/{id}/     - Lösche Link
```

## 🐛 Fehlerbehebung

### Datenbank-Fehler
```bash
# Migrationen zurücksetzen
python manage.py migrate core zero

# Migrationen neu erstellen
python manage.py makemigrations
python manage.py migrate
```

### Redis-Verbindungsfehler
```bash
# Redis Status prüfen
redis-cli ping

# Redis neu starten
docker-compose restart redis
```

### Speicherplatz voll
```bash
# Alte Versionen löschen
python manage.py cleanup_old_versions --days=30

# Papierkorb leeren
python manage.py cleanup_trash
```

## 📚 Weitere Ressourcen

- [Django Dokumentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Celery Dokumentation](https://docs.celeryproject.org/)

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert. Siehe `LICENSE` für Details.

## 🤝 Beitragen

Beiträge sind willkommen! Bitte erstellen Sie einen Pull Request oder öffnen Sie ein Issue.

## 📧 Support

Bei Fragen oder Problemen können Sie:
- Ein Issue auf GitHub öffnen
- Die Dokumentation konsultieren
- Den Community-Forum besuchen

---

**Viel Spaß mit CloudService! 🚀**
