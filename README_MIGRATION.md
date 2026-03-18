# 🔄 Vollständige Migrations-Anleitung für Anfänger

**Alles was Sie wissen müssen um HelpDesk, Cloude oder beide auf das neue System zu migrieren**

> 📌 **Diese Anleitung für absolute Anfänger geschrieben** - Keine Vorkenntnisse notwendig!

---

## 📚 Inhaltsverzeichnis

1. [Was ist Migration und warum brauchen wir das?](#was-ist-migration)
2. [Sicherheit an erster Stelle - Backups](#sicherheit-zuerst)
3. [Schritt-für-Schritt Migration HelpDesk](#helpdesk-migration)
4. [Schritt-für-Schritt Migration Cloude](#cloude-migration)
5. [Gemeinsame Migration (HelpDesk + Cloude)](#gemeinsame-migration)
6. [Häufige Fehler und Lösungen](#fehlerbehandlung)
7. [Überprüfung - Alles funktioniert?](#überprüfung)

---

## <a name="was-ist-migration"></a>🎯 Was ist Migration und warum brauchen wir das?

### Das Problem

Sie haben aktuell zwei separate Systeme:

```
VORHER:
┌─────────────────────────────────────┐
│  HelpDesk                           │
│  (Eigene User-Datenbank)            │
│  ├─ User: john@example.com          │
│  ├─ User: marie@example.com         │
│  └─ User: hans@example.com          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Cloude                             │
│  (Eigene User-Datenbank)            │
│  ├─ User: john@example.com          │
│  ├─ User: alice@example.com         │
│  └─ User: bob@example.com           │
└─────────────────────────────────────┘
```

**Probleme:**
- ❌ Benutzer müssen sich in beiden Systemen anmelden
- ❌ Unterschiedliche Passwörter für jedes System
- ❌ Benutzerdaten sind dupliziert
- ❌ Verwaltung ist kompliziert

### Die Lösung

```
NACHHER:
┌─────────────────────────────────────┐
│  Gemeinsame User-Datenbank          │
│  (platform_auth)                    │
│  ├─ User: john@example.com          │
│  ├─ User: marie@example.com         │
│  ├─ User: hans@example.com          │
│  ├─ User: alice@example.com         │
│  └─ User: bob@example.com           │
└─────────────────────────────────────┘
         ↙                    ↘
    ┌────────────┐       ┌────────────┐
    │ HelpDesk   │       │  Cloude    │
    │ (Login OK) │       │ (Login OK) │
    └────────────┘       └────────────┘
```

**Vorteile:**
- ✅ Ein Login für beide Apps
- ✅ Ein einheitliches Passwort
- ✅ Einfachere Verwaltung
- ✅ Bessere Sicherheit (SSO)

### Was passiert bei der Migration?

**Die Migration kopiert alle Benutzerdaten** von den alten Systemen in die neue gemeinsame Datenbank:

```
Schritt 1: Backup erstellen (Sicherheit!)
           ↓
Schritt 2: Datenbank vorbereiten
           ↓
Schritt 3: Benutzer kopieren
           ↓
Schritt 4: Überprüfung
           ↓
Schritt 5: System testen
```

---

## <a name="sicherheit-zuerst"></a>⚠️ Sicherheit an erster Stelle - Backups

### 🔴 WICHTIG: Backup vor jeder Migration!

**Wenn etwas schief geht, können Sie mit einem Backup wiederherstellen!**

### Backup für HelpDesk erstellen

#### Methode 1: Einfach mit PhpMyAdmin (GUI - Empfohlen für Anfänger)

```
1. Öffnen Sie PhpMyAdmin
   → http://localhost/phpmyadmin/

2. Linke Seite: Wählen Sie "helpdesk_db"

3. Oben: Klick auf "Exportieren"

4. Einstellungen:
   ✓ "SQL" ist bereits ausgewählt
   ✓ "SQL-Kommentare" aktiviert

5. Klick auf "Ausführen"

6. Datei wird automatisch heruntergeladen
   → Speichern Sie sie an einem sicheren Ort!
   → z.B. C:\Backups\helpdesk_backup_2024_01_15.sql
```

**Fertig!** Sie haben jetzt ein Backup.

---

#### Methode 2: Mit dem Terminal/Command Prompt (für Fortgeschrittene)

```bash
# Linux/macOS:
mysqldump -u root -p helpdesk_db > helpdesk_backup_$(date +%Y_%m_%d).sql

# Windows (Command Prompt):
mysqldump -u root -p helpdesk_db > helpdesk_backup_2024_01_15.sql
```

**Hinweis:** Das System fragt Sie nach dem MariaDB-Root-Passwort.

---

### Backup für Cloude erstellen

#### Mit PhpMyAdmin:

Gleich wie HelpDesk, aber wählen Sie `cloudservice_db` statt `helpdesk_db`.

---

### 💾 Backup überprüfen

Kontrollieren Sie, dass der Backup-Datei erstellt wurde:

```
Windows:  Gehen Sie zu C:\Backups\ und sehen Sie cloudservice_backup_2024_01_15.sql
Linux:    ls -lh backup*.sql    (sollte mehrere Dateien zeigen)
```

**Größe prüfen:**
- Leeres System: 100-500 KB
- Mit Daten: 1-10 MB
- Sehr großes System: 10-100+ MB

✅ Wenn die Datei existiert und größer als 10 KB ist → Backup erfolgreich!

---

## <a name="helpdesk-migration"></a>🎯 Schritt-für-Schritt: HelpDesk Migrieren

### Voraussetzungen

```
✓ Backup erstellt (siehe oben)
✓ HelpDesk läuft und funktioniert
✓ Benutzer können sich einloggen
✓ Alle Tickets/Daten sind vorhanden
```

### Phase 1: Vorbereitung (5 Minuten)

#### Schritt 1: platform_auth Package installieren

Das neue "Benutzerverwaltungs-System" muss installiert werden.

**Öffnen Sie das Terminal/Command Prompt:**

```bash
# Windows (Command Prompt oder PowerShell):
cd C:\Users\YourUser\PycharmProjects\HelpDesk
pip install -e C:\Users\YourUser\PycharmProjects\django-platform-auth

# Linux/macOS:
cd ~/PycharmProjects/HelpDesk
pip install -e ~/PycharmProjects/django-platform-auth
```

**Erwartete Ausgabe:**
```
Successfully installed django-platform-auth-0.1.0
```

❌ **Fehler "No module named django"?**
- Django ist nicht installiert
- Lösung: `pip install Django`

#### Schritt 2: requirements.txt updaten

Öffnen Sie die Datei `requirements.txt` in HelpDesk mit einem Editor:

```
C:\Users\YourUser\PycharmProjects\HelpDesk\requirements.txt
```

Suchen Sie die Zeile mit `django-platform-auth` und `mysqlclient`.

Falls nicht vorhanden, fügen Sie folgende Zeilen am Ende ein:

```
django-platform-auth>=0.1.0
mysqlclient>=2.2.0
```

Speichern Sie die Datei.

---

### Phase 2: Konfiguration (10 Minuten)

#### Schritt 3: settings.py updaten

Öffnen Sie die Datei:
```
C:\Users\YourUser\PycharmProjects\HelpDesk\helpdesk\settings.py
```

**Änderung 1: platform_auth zu INSTALLED_APPS hinzufügen**

Suchen Sie die Zeile mit `INSTALLED_APPS = [`

Fügen Sie `'platform_auth',` **ganz oben** ein:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Platform Authentication - MUST BE BEFORE OTHER APPS!
    'platform_auth',

    # Third-party apps
    # 'rest_framework',

    # Local apps
    'apps.accounts',
    'apps.tickets',
    'apps.knowledge',
    'apps.chat',
    'apps.admin_panel',
    'apps.main',
]
```

**Wichtig:** `'platform_auth',` muss VOR `'apps.accounts'` stehen!

---

**Änderung 2: AUTH_USER_MODEL updaten**

Suchen Sie diese Zeile (ungefähr Zeile 167):

```python
# ALT:
AUTH_USER_MODEL = 'accounts.User'

# NEU:
AUTH_USER_MODEL = 'platform_auth.User'
```

Ersetzen Sie die Zeile.

---

**Änderung 3: JWT-Konfiguration hinzufügen**

Suchen Sie nach `AUTH_PASSWORD_VALIDATORS`.

Fügen Sie NACH dieser Sektion folgendes ein:

```python
# JWT/SSO Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY', SECRET_KEY),
}

# SSO Cookie Configuration
SSO_COOKIE_NAME = 'platform_sso_token'
SSO_COOKIE_DOMAIN = os.getenv('SSO_COOKIE_DOMAIN', None)
SSO_COOKIE_SECURE = not DEBUG
SSO_COOKIE_SAMESITE = 'Lax'
```

**Hinweis:** Falls `timedelta` nicht importiert ist, fügen Sie oben in der Datei hinzu:
```python
from datetime import timedelta
```

---

#### Schritt 4: Speichern Sie alle Änderungen!

Speichern Sie `settings.py` mit Ctrl+S (oder Cmd+S auf Mac).

---

### Phase 3: Datenbankmigrationen (10 Minuten)

#### Schritt 5: Neue Tabellen erstellen

Öffnen Sie das Terminal im HelpDesk-Verzeichnis:

```bash
# Windows:
cd C:\Users\YourUser\PycharmProjects\HelpDesk

# Linux/macOS:
cd ~/PycharmProjects/HelpDesk
```

Führen Sie diesen Befehl aus:

```bash
python manage.py migrate platform_auth
```

**Erwartete Ausgabe:**
```
Operations to perform:
  Apply all migrations: platform_auth
Running migrations:
  Applying platform_auth.0001_initial... OK
```

✅ Wenn "OK" erscheint → Erfolgreich!

❌ **Fehler "No such table"?**
- Datenbank-Verbindung ist falsch
- Überprüfen Sie die DATABASE_URL in .env

---

#### Schritt 6: Data-Migration erstellen

Dies ist die Datei, die Ihre Benutzer kopiert.

```bash
python manage.py makemigrations accounts --empty --name migrate_to_platform_auth
```

**Erwartete Ausgabe:**
```
Migrations for 'accounts':
  apps/accounts/migrations/0007_migrate_to_platform_auth.py
```

---

#### Schritt 7: Migration-Datei bearbeiten

Öffnen Sie die gerade erstellte Datei:
```
C:\Users\YourUser\PycharmProjects\HelpDesk\apps\accounts\migrations\0007_migrate_to_platform_auth.py
```

Ersetzen Sie den GESAMTEN Inhalt mit diesem Code:

```python
from django.db import migrations
import logging

logger = logging.getLogger(__name__)


def migrate_users(apps, schema_editor):
    """Copy users from accounts.User to platform_auth.User"""
    OldUser = apps.get_model('accounts', 'User')
    NewUser = apps.get_model('platform_auth', 'User')

    old_users = OldUser.objects.all()
    print(f"\n{'='*60}")
    print(f"🔄 Migrating {old_users.count()} users...")
    print(f"{'='*60}\n")

    migrated_count = 0
    error_count = 0

    for old_user in old_users:
        try:
            # Check if already exists
            if NewUser.objects.filter(id=old_user.id).exists():
                print(f"⚠️  User {old_user.email} already exists, skipping...")
                continue

            # Create new user with all data
            new_user = NewUser.objects.create(
                id=old_user.id,
                username=old_user.username,
                email=old_user.email,
                first_name=old_user.first_name,
                last_name=old_user.last_name,
                password=old_user.password,
                is_active=old_user.is_active,
                is_staff=old_user.is_staff,
                is_superuser=old_user.is_superuser,
                last_login=old_user.last_login,
                created_at=old_user.created_at,
                updated_at=old_user.updated_at,
                # HelpDesk-specific fields
                role=old_user.role,
                support_level=old_user.support_level,
                phone=getattr(old_user, 'phone', ''),
                department=getattr(old_user, 'department', ''),
                location=getattr(old_user, 'location', ''),
                email_verified=getattr(old_user, 'email_verified', False),
                force_password_change=getattr(old_user, 'force_password_change', False),
                last_activity=getattr(old_user, 'last_activity', None),
                street=getattr(old_user, 'street', ''),
                postal_code=getattr(old_user, 'postal_code', ''),
                city=getattr(old_user, 'city', ''),
                country=getattr(old_user, 'country', 'Deutschland'),
            )

            # Copy groups and permissions
            new_user.groups.set(old_user.groups.all())
            new_user.user_permissions.set(old_user.user_permissions.all())

            migrated_count += 1
            print(f"✓ Migrated: {old_user.email} (ID: {old_user.id})")

        except Exception as e:
            error_count += 1
            print(f"✗ Error migrating {old_user.email}: {str(e)}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"✅ Migration complete!")
    print(f"   Migrated: {migrated_count} users")
    print(f"   Errors: {error_count}")
    print(f"{'='*60}\n")


def rollback_migration(apps, schema_editor):
    """Rollback: delete migrated users"""
    NewUser = apps.get_model('platform_auth', 'User')
    count = NewUser.objects.count()
    NewUser.objects.all().delete()
    print(f"Rolled back {count} users")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_user_last_activity'),
        ('platform_auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_users, rollback_migration),
    ]
```

**Speichern Sie die Datei.**

---

#### Schritt 8: Migration ausführen

Im Terminal, führen Sie aus:

```bash
python manage.py migrate accounts
```

**Das ist die wichtigste Schritt - Ihre Benutzer werden jetzt kopiert!**

Erwartete Ausgabe:
```
============================================================
🔄 Migrating 25 users...
============================================================

✓ Migrated: john@example.com (ID: 1)
✓ Migrated: marie@example.com (ID: 2)
✓ Migrated: hans@example.com (ID: 3)
...

============================================================
✅ Migration complete!
   Migrated: 25 users
   Errors: 0
============================================================

Running migrations:
  Applying accounts.0007_migrate_to_platform_auth... OK
```

✅ **Erfolgreich, wenn keine Fehler und "Errors: 0"**

---

### Phase 4: Überprüfung (5 Minuten)

#### Schritt 9: Benutzer überprüfen

Öffnen Sie die Django Shell:

```bash
python manage.py shell
```

Geben Sie diese Befehle ein:

```python
from django.contrib.auth import get_user_model

User = get_user_model()

# Wie viele Benutzer wurden migriert?
print(f"Total users: {User.objects.count()}")

# Liste alle Benutzer auf
for user in User.objects.all():
    print(f"  - {user.email} (Role: {user.role})")

# Test: Kann ein Benutzer sich anmelden?
admin = User.objects.filter(role='admin').first()
if admin:
    print(f"\nTesting admin user: {admin.email}")
    # PASSWORT NICHT EINGEBEN - nur testen, ob der Benutzer existiert
    print(f"  ID: {admin.id}")
    print(f"  Role: {admin.role}")

# Beenden Sie die Shell
exit()
```

**Erwartete Ausgabe:**
```
Total users: 25

  - john@example.com (Role: customer)
  - marie@example.com (Role: support_agent)
  - hans@example.com (Role: admin)
  ...

Testing admin user: hans@example.com
  ID: 3
  Role: admin
```

---

#### Schritt 10: Server starten und testen

```bash
python manage.py runserver
```

Öffnen Sie im Browser: `http://localhost:8000/auth/login/`

**Versuchen Sie sich anzumelden:**
- Email: (Eine der migrierten E-Mails)
- Passwort: (Das gleiche wie vorher)

✅ **Wenn Login funktioniert → Migration erfolgreich!**

❌ **Wenn Login nicht funktioniert?**
- Siehe [Fehlerbehandlung](#fehlerbehandlung) unten

---

## <a name="cloude-migration"></a>🎯 Schritt-für-Schritt: Cloude Migrieren

Die Cloude-Migration ist ähnlich wie HelpDesk, aber **komplexer**, weil Cloude's Standard User + UserProfile in ein einziges Modell konvertiert werden müssen.

### Voraussetzungen

```
✓ HelpDesk ist bereits migriert (oder Sie migrieren beide parallel)
✓ Backup von cloudservice_db erstellt
✓ Cloude läuft und funktioniert
```

### Phase 1: Vorbereitung

#### Schritt 1: platform_auth installieren

```bash
# Windows:
cd C:\Users\YourUser\PycharmProjects\Cloude

# Linux/macOS:
cd ~/PycharmProjects/Cloude

# Für beide:
pip install -e ../django-platform-auth
```

---

#### Schritt 2: settings.py in Cloude aktualisieren

Öffnen Sie: `C:\Users\YourUser\PycharmProjects\Cloude\cloudservice\config\settings.py`

**Änderung 1:** Fügen Sie `'platform_auth',` zu INSTALLED_APPS hinzu (ganz oben):

```python
INSTALLED_APPS = [
    'platform_auth',  # ADD THIS FIRST!

    'django.contrib.admin',
    'django.contrib.auth',
    # ... rest of apps
]
```

**Änderung 2:** Suchen Sie nach `AUTH_USER_MODEL` und ändern Sie:

```python
# Suchen Sie diese Zeile (ungefähr Zeile 140):
# AUTH_USER_MODEL = ... (falls vorhanden)

# Oder fügen Sie hinzu:
AUTH_USER_MODEL = 'platform_auth.User'
```

---

#### Schritt 3: Datenbank-Migration erstellen

```bash
python manage.py makemigrations accounts --empty --name migrate_to_platform_auth
```

Öffnen Sie die erstellte Datei: `cloudservice/accounts/migrations/XXXX_migrate_to_platform_auth.py`

Ersetzen Sie mit diesem Code (ähnlich wie HelpDesk, aber für Cloude):

```python
from django.db import migrations
from django.utils import timezone


def migrate_users(apps, schema_editor):
    """Merge User + UserProfile into platform_auth.User"""
    OldUser = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('accounts', 'UserProfile')
    NewUser = apps.get_model('platform_auth', 'User')

    old_users = OldUser.objects.all()
    print(f"\n{'='*60}")
    print(f"🔄 Migrating {old_users.count()} Cloude users...")
    print(f"{'='*60}\n")

    migrated_count = 0
    error_count = 0

    # Mapping von Cloude-Rollen zu neuen Rollen
    role_mapping = {
        'admin': 'admin',
        'moderator': 'moderator',
        'user': 'user',
    }

    for old_user in old_users:
        try:
            if NewUser.objects.filter(id=old_user.id).exists():
                print(f"⚠️  User {old_user.email} already exists, skipping...")
                continue

            # Get associated UserProfile
            try:
                profile = UserProfile.objects.get(user=old_user)
            except UserProfile.DoesNotExist:
                profile = None
                print(f"⚠️  No profile for {old_user.email}, creating defaults...")

            # Create new user combining User + UserProfile
            new_user = NewUser.objects.create(
                id=old_user.id,
                username=old_user.username,
                email=old_user.email,
                first_name=old_user.first_name,
                last_name=old_user.last_name,
                password=old_user.password,
                is_active=old_user.is_active,
                is_staff=old_user.is_staff,
                is_superuser=old_user.is_superuser,
                last_login=old_user.last_login,
                created_at=profile.created_at if profile else old_user.date_joined,
                # Cloude UserProfile fields
                role=role_mapping.get(profile.role, 'user') if profile else 'user',
                storage_quota=profile.storage_quota if profile else 5*1024*1024*1024,
                avatar=profile.avatar if profile else None,
                bio=profile.bio if profile else '',
                website=profile.website if profile else '',
                language=profile.language if profile else 'de',
                timezone=profile.timezone if profile else 'Europe/Berlin',
                theme=profile.theme if profile else 'auto',
                email_verified=profile.is_email_verified if profile else False,
                is_two_factor_enabled=profile.is_two_factor_enabled if profile else False,
            )

            migrated_count += 1
            print(f"✓ Migrated: {old_user.email}")

        except Exception as e:
            error_count += 1
            print(f"✗ Error: {old_user.email}: {str(e)}")

    print(f"\n{'='*60}")
    print(f"✅ Migration complete!")
    print(f"   Migrated: {migrated_count} users")
    print(f"   Errors: {error_count}")
    print(f"{'='*60}\n")


def rollback(apps, schema_editor):
    NewUser = apps.get_model('platform_auth', 'User')
    NewUser.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', 'previous_migration_name'),  # ← UPDATE THIS!
        ('platform_auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_users, rollback),
    ]
```

**⚠️ WICHTIG:** Ersetzen Sie `'previous_migration_name'` mit der letzten Migration von Cloude's accounts app.

Um die letzte Migration zu finden, schauen Sie in: `cloudservice/accounts/migrations/` und suchen Sie die Nummer der letzten Datei (z.B. `0006_...` → dann ist es `'0006_...'`).

---

#### Schritt 4: Migration ausführen

```bash
python manage.py migrate accounts
```

Erwartete Ausgabe: ✅ Ähnlich wie HelpDesk

---

## <a name="gemeinsame-migration"></a>🎯 Gemeinsame Migration (HelpDesk + Cloude)

Falls Sie **beide Apps zusammen** migrieren möchten:

### Timeline

```
Schritt 1: Backup (BEIDE Apps)              ← 10 Min
Schritt 2: HelpDesk migrieren                ← 30 Min
Schritt 3: Cloude migrieren                  ← 30 Min
Schritt 4: Docker-Compose aufsetzen          ← 30 Min
Schritt 5: Tests                             ← 15 Min
─────────────────────────────────────────────
TOTAL:                                        ← ~2 Stunden
```

### Ablauf

1. **Backup BEIDER Datenbanken**
   ```bash
   # helpdesk_db UND cloudservice_db
   ```

2. **HelpDesk migrieren** (folgen Sie der Anleitung oben)

3. **Cloude migrieren** (folgen Sie der Anleitung oben)

4. **Docker-Compose starten**
   ```bash
   cd unified-install
   ./setup.sh  # oder setup.bat für Windows
   ```

5. **SSO testen**
   - Login in HelpDesk
   - Browser öffnet Cloude
   - Sie sollten bereits eingeloggt sein!

---

## <a name="fehlerbehandlung"></a>❌ Häufige Fehler und Lösungen

### Fehler 1: "ProgrammingError: no such table"

**Problem:**
```
django.db.utils.ProgrammingError: no such table: accounts_user
```

**Ursache:** Alte Tabelle existiert nicht mehr oder ist nicht zugänglich

**Lösung:**
```bash
# Überprüfen Sie die Datenbankverbindung
python manage.py dbshell

# In MySQL:
SHOW TABLES;
SHOW TABLES LIKE '%user%';

# Falls Tabelle fehlt, Backup zurückstellen
```

---

### Fehler 2: "IntegrityError: Duplicate entry"

**Problem:**
```
IntegrityError: (1062, "Duplicate entry 'john@example.com' for key 'email'")
```

**Ursache:** Benutzer wurde bereits migriert oder existiert doppelt

**Lösung:**
```python
# In Django Shell:
python manage.py shell

from django.contrib.auth import get_user_model
User = get_user_model()

# Überprüfen Sie doppelte Einträge
from django.db.models import Count
duplicates = User.objects.values('email').annotate(count=Count('email')).filter(count__gt=1)
print(duplicates)

# Doppelte löschen (vorsichtig!)
# für duplicate in duplicates:
#     User.objects.filter(email=duplicate['email'])[1:].delete()
```

---

### Fehler 3: "ModuleNotFoundError: No module named 'platform_auth'"

**Problem:**
```
ModuleNotFoundError: No module named 'platform_auth'
```

**Ursache:** Package nicht installiert

**Lösung:**
```bash
# Neu installieren
pip install -e C:\Path\To\django-platform-auth

# Oder:
pip uninstall django-platform-auth
pip install -e C:\Path\To\django-platform-auth
```

---

### Fehler 4: "No such table: platform_users"

**Problem:**
```
OperationalError: no such table: platform_users
```

**Ursache:** platform_auth Migration wurde nicht ausgeführt

**Lösung:**
```bash
# Zuerst diese Migration
python manage.py migrate platform_auth

# Dann die other migrations
python manage.py migrate
```

---

### Fehler 5: Login funktioniert nicht nach Migration

**Problem:**
```
Login schlägt fehl, aber Benutzer existiert
```

**Ursache:** Passwort-Hash wurde nicht korrekt kopiert

**Lösung:**
```python
# Test in Django Shell:
from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.get(email='john@example.com')

# Test mit einem bekannten Password
result = user.check_password('correct_password_here')
print(result)  # Sollte True sein

# Falls False, müssen Sie das Passwort zurücksetzen
user.set_password('new_password')
user.save()
print("Password reset erfolgreich")
```

---

### Fehler 6: "FOREIGN KEY constraint fails"

**Problem:**
```
IntegrityError: (1452, "Cannot add or update a child row: a foreign key constraint fails")
```

**Ursache:** Ein Benutzer wird von Tickets/Dateien referenziert, wurde aber nicht migriert

**Lösung:**
```bash
# Überprüfen Sie, welche Benutzer referenziert werden
python manage.py shell

from apps.tickets.models import Ticket
from django.contrib.auth import get_user_model

User = get_user_model()

# Alle User IDs die in Tickets verwendet werden
used_ids = Ticket.objects.values_list('created_by_id', flat=True).distinct()

# Überprüfen Sie, welche IDs nicht migriert wurden
missing = []
for uid in used_ids:
    if not User.objects.filter(id=uid).exists():
        missing.append(uid)

print(f"Missing users: {missing}")

# Stellen Sie den Backup zurück und versuchen Sie es erneut
```

---

## <a name="überprüfung"></a>✅ Überprüfung - Alles funktioniert?

### Checkliste nach der Migration

```
☐ Backup erstellt
☐ settings.py aktualisiert
☐ platform_auth installiert
☐ Migrationen ausgeführt (keine Fehler)
☐ Benutzer in neuer Tabelle vorhanden
☐ Login funktioniert
☐ Alle Daten vorhanden (Tickets, Dateien, etc.)
☐ Benutzerrollen erhalten
☐ Email-Funktionen arbeiten
```

### Test-Szenarien

#### Test 1: Admin-Benutzer

```bash
python manage.py shell

from django.contrib.auth import get_user_model
User = get_user_model()

admin = User.objects.get(is_superuser=True)
print(f"Admin: {admin.email}")
print(f"Can login: {admin.check_password('password')}")  # Nur wenn Sie das Passwort kennen!
```

#### Test 2: Alle Benutzer können sich anmelden

```bash
# Für jeden Benutzer testen
python manage.py shell

from django.contrib.auth import authenticate

user = authenticate(username='john@example.com', password='password')
print(f"Login result: {user}")  # Sollte User-Objekt sein, nicht None
```

#### Test 3: Benutzer-Daten intakt

```bash
python manage.py shell

from apps.tickets.models import Ticket
from django.contrib.auth import get_user_model

User = get_user_model()

# Zählen Sie Tickets
ticket_count = Ticket.objects.count()
print(f"Total tickets: {ticket_count}")

# Überprüfen Sie, dass Tickets noch Besitzer haben
tickets_without_owner = Ticket.objects.filter(created_by__isnull=True).count()
print(f"Tickets without owner: {tickets_without_owner}")  # Sollte 0 sein!
```

---

## 📞 Wenn etwas nicht funktioniert

### Debugging-Schritte

1. **Überprüfen Sie die Logs**
   ```bash
   # Terminal-Fenster mit:
   python manage.py runserver
   # Zeigt alle Fehler in Echtzeit
   ```

2. **Datenbank direkt überprüfen**
   ```bash
   python manage.py dbshell
   SELECT COUNT(*) FROM platform_users;
   SELECT COUNT(*) FROM accounts_user;
   ```

3. **Migration rückgängig machen**
   ```bash
   python manage.py migrate accounts 0006
   # Geht zurück zu vorheriger Version
   ```

4. **Backup zurückstellen**
   ```bash
   # Falls alles falsch ist:
   # 1. Datenbank löschen
   # 2. Backup importieren
   # 3. Neu beginnen
   ```

---

## 📚 Weitere Ressourcen

- [Django Migrations Dokumentation](https://docs.djangoproject.com/en/5.0/topics/migrations/)
- [platform_auth README](./django-platform-auth/README.md)
- [Docker-Compose Setup](./unified-install/README.md)

---

**Viel Erfolg bei der Migration! 🚀**

Bei Fragen oder Problemen, überprüfen Sie diese Checkliste nochmal und folgen Sie den Schritten langsam und sorgfältig.
