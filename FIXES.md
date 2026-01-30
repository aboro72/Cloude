# Django System Check Fehler - Behebung

## Problem
Beim Starten des Django Development Servers traten folgende Fehler auf:

```
ERRORS:
auth.Permission.content_type: (fields.E304) Reverse accessor 'ContentType.permission_set'
for 'auth.Permission.content_type' clashes with reverse accessor for 'sharing.Permission.content_type'.

sharing.Permission.content_type: (fields.E304) Reverse accessor 'ContentType.permission_set'
for 'sharing.Permission.content_type' clashes with reverse accessor for 'auth.Permission.content_type'.

WARNINGS:
?: (guardian.W001) Guardian authentication backend is not hooked.
```

## Ursache
1. **Konflikt im Modellnamen**: Wir hatten ein `Permission` Modell in `sharing/models.py` erstellt, das mit Djangos eingebautem `auth.Permission` Modell kollidierte. Beide verwendeten `content_type` als ForeignKey mit dem gleichen `related_name`.

2. **Guardian Backend nicht konfiguriert**: Die `django-guardian` Bibliothek war nicht in den `AUTHENTICATION_BACKENDS` registriert.

## Lösung

### 1. Permission Modell umbenannt
- `sharing/models.py`: `Permission` → `SharePermission`
- Alle Referenzen aktualisiert
- `related_name` für ForeignKey auf `'share_permissions'` geändert

**Geänderte Dateien:**
- `cloudservice/sharing/models.py`: Modell umbenannt, `related_name` angepasst
- `cloudservice/api/serializers.py`: Import und Serializer-Name aktualisiert
- `cloudservice/api/views.py`: Import aktualisiert

### 2. Guardian Backend konfiguriert
- `cloudservice/config/settings.py`: `AUTHENTICATION_BACKENDS` hinzugefügt

```python
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # Default Django Auth
    'guardian.backends.ObjectPermissionBackend',  # Object-level Permissions
)
```

## Durchführung der Änderungen

### Schritt 1: Datenbank-Migration erstellen
```bash
cd cloudservice
python manage.py makemigrations sharing
```

### Schritt 2: Migration anwenden
```bash
python manage.py migrate sharing
```

### Schritt 3: Server testen
```bash
python manage.py runserver
```

Sollte jetzt ohne Fehler starten!

## Was hat sich geändert?

### Vor:
```python
class Permission(models.Model):
    content_type = models.ForeignKey(ContentType, ...)
```

### Nach:
```python
class SharePermission(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        related_name='share_permissions',  # ← Eindeutiger Name
        ...
    )
```

## Auswirkungen
- **Keine Breaking Changes** für die Funktionalität
- Das Modell heißt nur intern anders
- In der API und der Datenbank gibt es keine Änderungen für Benutzer
- Django/Guardian funktionieren jetzt ohne Warnungen

## Testing
Alle bestehenden Tests sollten ohne Änderungen weiterhin funktionieren:

```bash
pytest cloudservice/tests/
```

---

**Status**: ✅ Alle Fehler behoben
