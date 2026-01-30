# CloudService - Demo Benutzer

## Verfügbare Demo-Konten

### Admin Benutzer
```
Username: admin
Password: Admin123!
Email: admin@cloudservice.local
Speicher: 10 GB
Rolle: Administrator
```

**Zugriff:**
- Admin Panel: http://localhost:8000/admin/
- Dashboard: http://localhost:8000/core/ (nach Login)
- API: http://localhost:8000/api/ (mit Token)

**Admin-Funktionen:**
- ✅ Alle Dateien verwalten
- ✅ Alle Benutzer sehen
- ✅ System-Einstellungen
- ✅ Benutzerverwaltung

---

### Demo Benutzer
```
Username: demo
Password: Demo123!
Email: demo@cloudservice.local
Speicher: 5 GB
Rolle: Regular User
```

**Zugriff:**
- Login: http://localhost:8000/accounts/login/
- Dashboard: http://localhost:8000/core/ (nach Login)
- Dateiverwaltung: http://localhost:8000/storage/
- API: http://localhost:8000/api/ (mit Token)

**Benutzer-Funktionen:**
- ✅ Dateien hochladen/downloaden
- ✅ Ordner erstellen
- ✅ Dateien mit anderen teilen
- ✅ Öffentliche Links erstellen
- ✅ Profil verwalten

---

## 🌐 Schnelllinks

| Seite | URL | Beschreibung |
|-------|-----|------------|
| **Home** | http://localhost:8000/ | Landing Page |
| **Login** | http://localhost:8000/accounts/login/ | Anmeldung |
| **Admin Panel** | http://localhost:8000/admin/ | Django Admin |
| **Dashboard** | http://localhost:8000/core/ | Benutzer-Dashboard |
| **Dateien** | http://localhost:8000/storage/ | Dateiverwaltung |
| **API Docs** | http://localhost:8000/api/docs/ | Swagger UI |
| **API ReDoc** | http://localhost:8000/api/redoc/ | ReDoc Doku |

---

## 🧪 API Testing mit Swagger

### 1. Token erhalten

1. Öffne: http://localhost:8000/api/docs/
2. Suche nach `/api/auth/token/` Endpoint
3. Klicke "Try it out"
4. Gib ein:
   ```json
   {
     "username": "admin",
     "password": "Admin123!"
   }
   ```
5. Klicke "Execute"
6. Kopiere den `access` Token

### 2. Autorize mit Token

1. Klicke oben auf "Authorize"
2. Gib ein: `Bearer YOUR_TOKEN`
3. Klicke "Authorize"

### 3. API Endpoints testen

Jetzt kannst du alle Endpoints testen:
- `GET /api/files/` - Dateien abrufen
- `POST /api/files/` - Datei hochladen
- `GET /api/folders/` - Ordner abrufen
- Und viel mehr...

---

## 📝 Curl Commands

### Admin Token erhalten

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

### Mit Token API aufrufen

```bash
TOKEN="your_token_here"

# Dateien abrufen
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/files/

# Ordner abrufen
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/folders/

# Shares abrufen
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/shares/
```

---

## 🔐 Passwort ändern

### Web-Interface
1. Login mit Benutzer
2. Gehe zu `/accounts/profile/password/`
3. Gib altes + neues Passwort ein

### CLI
```bash
cd cloudservice
python manage.py changepassword admin
```

---

## 👥 Weitere Benutzer erstellen

### Django Admin
1. Öffne http://localhost:8000/admin/
2. Login als `admin` / `Admin123!`
3. Gehe zu "Users"
4. Klicke "Add User"
5. Fülle Formular aus

### Benutzer-Registrierung
1. Öffne http://localhost:8000/accounts/register/
2. Fülle Formular aus
3. Klicke "Registrieren"

---

## 🗑️ Benutzer löschen

```bash
cd cloudservice
python manage.py shell

from django.contrib.auth.models import User
User.objects.filter(username='demo').delete()
```

---

## 📊 Benutzer-Informationen ansehen

```bash
cd cloudservice
python manage.py shell

from django.contrib.auth.models import User
users = User.objects.all()
for user in users:
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Role: {user.profile.role}")
    print(f"Storage: {user.profile.get_storage_used_mb():.2f} MB / {user.profile.storage_quota / (1024*1024*1024):.1f} GB")
    print("---")
```

---

## 🚀 Nächste Schritte

1. **Datei hochladen** - Gehe zu /storage/ und lade Test-Datei hoch
2. **Ordner erstellen** - Erstelle neue Ordnerstruktur
3. **Datei teilen** - Teile Datei mit anderem Benutzer
4. **Public Link** - Erstelle öffentlichen Link
5. **API testen** - Nutze Swagger UI zum Testen

---

**Viel Spaß beim Testen! 🎉**
