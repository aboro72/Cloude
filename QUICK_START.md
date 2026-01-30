# CloudService - Quick Start Guide

## ✅ Status: Fertig zur Entwicklung

Dein CloudService-Projekt ist vollständig konfiguriert und bereit für die Entwicklung!

## 🚀 Server starten

```bash
cd cloudservice
python manage.py runserver
```

Der Server läuft dann unter `http://localhost:8000`

## 📊 Admin Interface

- **URL**: http://localhost:8000/admin/
- **Username**: `admin`
- **Passwort**: (wurde beim Setup erstellt, kann mit `python manage.py changepassword admin` geändert werden)

## 🔌 API Endpoints

- **REST API Root**: http://localhost:8000/api/
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## 🗂️ Projektstruktur

```
cloudservice/
├── core/              # Dateiverwaltung
├── accounts/          # Benutzer & Auth
├── storage/           # Speicherverwaltung
├── sharing/           # Sharing & Permissions
├── api/               # REST API
└── manage.py
```

## 💾 Datenbank

Für die **Entwicklung** wird **SQLite** verwendet (einfacher, kein Setup nötig).
Für **Production** nutze **PostgreSQL** (siehe DEPLOYMENT.md).

### Datenbank zurücksetzen

```bash
# Alle Daten löschen und neu erstellen
python manage.py flush --noinput
python manage.py migrate

# Neuer Admin User
python manage.py createsuperuser
```

## 📝 Wichtige Management Commands

```bash
# Migrationen erstellen
python manage.py makemigrations

# Migrationen anwenden
python manage.py migrate

# Superuser erstellen
python manage.py createsuperuser

# Shell (Django REPL)
python manage.py shell

# Tests ausführen
pytest

# Tests mit Coverage
pytest --cov=cloudservice
```

## 🧪 API testen

### Mit curl:

```bash
# User erstellen
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'

# Token erhalten
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# API aufrufen mit Token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/files/
```

### Mit Python (requests):

```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/token/',
    json={'username': 'admin', 'password': 'admin'})
token = response.json()['access']

# API Request
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/api/files/', headers=headers)
print(response.json())
```

## 🔄 Async Tasks (Celery)

Für die Entwicklung optional:

```bash
# Celery Worker starten (separates Terminal)
celery -A config worker --loglevel=info

# Celery Beat Scheduler (separates Terminal)
celery -A config beat --loglevel=info

# Redis (separates Terminal)
redis-server
```

## 📦 Dependencies hinzufügen

```bash
# Neues Package installieren
pip install package_name

# requirements.txt aktualisieren
pip freeze > requirements.txt

# Dev-Tools
pip install -r requirements-dev.txt
```

## 🐛 Häufige Probleme

### "No such table" Fehler
```bash
python manage.py migrate
```

### ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### Port 8000 ist bereits in Benutzung
```bash
# Anderen Port verwenden
python manage.py runserver 8001
```

### Statische Dateien nicht laden
```bash
python manage.py collectstatic --noinput
```

## 📚 Weitere Ressourcen

- [README.md](README.md) - Vollständige Projekt-Übersicht
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technische Architektur
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production Deployment
- [FIXES.md](FIXES.md) - Behobene Fehler
- [Django Dokumentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)

## ✨ Nächste Schritte

1. **Frontend entwickeln** - HTML/CSS/JavaScript Templates
2. **Tests schreiben** - Unit & Integration Tests
3. **Features testen** - API mit Swagger UI testen
4. **Deployment vorbereiten** - Docker Setup testen

---

**Viel Spaß beim Entwickeln! 🚀**
