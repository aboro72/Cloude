# Clock Plugin Debug Notes

**Status**: ❌ Plugin funktioniert nicht
**Datum**: 2026-01-30
**Fortschritt**: 50% - Plugin lädt, aber Hooks werden nicht auf HTTP-Requests registriert

---

## 🔴 Aktuelles Problem

Das Clock Plugin ist installiert und aktiviert, aber die Uhr wird nicht auf der Seite angezeigt.

- HTTP Requests returnen 200 OK
- Plugin ist in DB: `enabled: True`, `status: active`
- Plugin-Dateien sind extrahiert
- **ABER**: Die Hooks werden nicht registriert wenn auf HTTP GET `/storage/file/10/` aufgerufen wird

---

## ✅ Was bereits funktioniert

### 1. Plugin Installation
```
✅ Plugin Name: Analog Clock Preview
✅ Slug: clock-preview
✅ Status: active
✅ Module Name: clock_preview
✅ Extracted Path: C:\Users\aborowczak\PycharmProjects\Cloude\plugins\installed\clock_preview\
```

### 2. Manuelle Hook-Registrierung
Wenn wir die `ready()` Methode MANUELL aufrufen:
```python
from clock_preview.apps import ClockPreviewConfig
import clock_preview

config = ClockPreviewConfig('clock_preview', clock_preview)
config.ready()  # ← Hooks werden registriert!

# ✅ Result: 1 Handler registriert
```

### 3. PluginLoader funktioniert
```python
loader = PluginLoader()
loader.load_plugin(str(plugin.id))  # Ruft ready() auf
# ✅ Result: 1 Handler registriert
```

---

## ❌ Das funktioniert nicht

### Hook-Registry beim HTTP-Request
Wenn man auf eine `.plug` Datei klickt und `/storage/file/10/` aufgerufen wird:
```python
from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER

handlers = hook_registry.get_handlers(FILE_PREVIEW_PROVIDER)
# ❌ Result: 0 Handler gefunden!
```

---

## 📋 Vermutete Probleme

### 1. Django-Server wurde nicht neu gestartet
Die `HookRegistry` ist ein Singleton und wird beim Django-Startup initialisiert:
```python
class HookRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._hooks = {}
        return cls._instance
```

**Hypothese**: Wenn der Server läuft und wir das Plugin laden, wird die neue Instanz nicht mit der bestehenden synchronisiert.

### 2. Hot-loading registriert Hooks nicht richtig
Die `PluginLoader.load_plugin()` ruft `ready()` auf, aber vielleicht:
- Wird die richtige Instanz der HookRegistry nicht verwendet
- Die Module sind noch im `sys.modules` Cache
- Es gibt einen Import-Fehler, der stillschweigend ignoriert wird

### 3. Sys.modules Pfade falsch
Das Plugin wird geladen mit `module_name = 'clock_preview'`, aber die Imports nutzen relative Pfade.

---

## 🔧 Lösung zum Testen (morgen)

### Schritt 1: Server komplett neustarten
```bash
# Terminal, wo runserver läuft:
Ctrl+C  # Server stoppen

# Dann neu starten:
python manage.py runserver
```

### Schritt 2: Überprüfen ob Hooks registriert sind
```bash
cd cloudservice
python << 'EOF'
import os, sys
sys.path.insert(0, '..')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER

handlers = hook_registry.get_handlers(FILE_PREVIEW_PROVIDER)
print(f"Hooks registriert: {len(handlers)}")
if handlers:
    print("✅ Alles gut!")
else:
    print("❌ Hooks immer noch nicht registriert")
EOF
```

### Schritt 3: Falls noch nicht registriert - Debug-Logs
Schau auf dem Server-Terminal nach Fehlern wenn der Server startet:
```
# Suche nach diesen Zeilen:
"Initializing Clock Preview Plugin"
"Clock Preview Provider registered"
"Failed to initialize Clock Preview Plugin"  ← Falls vorhanden = FEHLER!
```

### Schritt 4: Falls Fehler sichtbar ist
Dann müssen wir die `apps.py` fixen. Das Problem könnte sein:
```python
# In clock_preview/apps.py, Zeile 27:
from clock_preview.handlers import ClockPreviewProvider  # ← Falscher Import-Pfad?
```

Sollte vielleicht sein:
```python
from .handlers import ClockPreviewProvider  # Relativer Import
```

---

## 📊 Debugging-Befehle für morgen

### Plugin Status überprüfen
```bash
cd cloudservice && python << 'EOF'
import os, sys
sys.path.insert(0, '..')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from plugins.models import Plugin

p = Plugin.objects.filter(slug='clock-preview').first()
print(f"Name: {p.name}")
print(f"Enabled: {p.enabled}")
print(f"Status: {p.status}")
print(f"Module: {p.module_name}")
print(f"Extracted: {p.extracted_path}")
EOF
```

### Hooks überprüfen
```bash
cd cloudservice && python << 'EOF'
import os, sys
sys.path.insert(0, '..')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER

handlers = hook_registry.get_handlers(FILE_PREVIEW_PROVIDER)
print(f"Handlers: {len(handlers)}")
for h in handlers:
    print(f"  - {h.__name__}")
EOF
```

### Plugin neuladen (falls nötig)
```bash
cd cloudservice && python << 'EOF'
import os, sys
sys.path.insert(0, '..')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from plugins.models import Plugin
from plugins.loader import PluginLoader

loader = PluginLoader()
plugin = Plugin.objects.filter(slug='clock-preview').first()

if plugin.enabled:
    loader.unload_plugin(str(plugin.id))
    print("Plugin unloaded")

loader.load_plugin(str(plugin.id))
print("Plugin reloaded")
EOF
```

---

## 📁 Wichtige Dateien

```
cloudservice/
├── plugins/
│   ├── hooks.py                          ← HookRegistry (Singleton)
│   ├── loader.py                         ← PluginLoader
│   ├── models.py                         ← Plugin DB Model
│   └── installed/
│       └── clock_preview/               ← ✅ Extrahiert hier
│           ├── __init__.py
│           ├── apps.py                  ← ready() Methode
│           ├── handlers.py              ← ClockPreviewProvider
│           └── plugin.json
└── storage/
    └── views.py (Zeile 112-149)         ← Wo Hooks abgefragt werden
```

---

## 🎯 Nächste Schritte (Priorität)

1. **[CRITICAL]** Server neustarten → Hooks überprüfen
2. **[HIGH]** Falls nicht registriert → Server-Logs auf Fehler checken
3. **[HIGH]** Falls ready() fehler hat → Import-Pfade in `apps.py` fixen
4. **[MEDIUM]** Falls immer noch nicht → Hot-loading Logik überprüfen

---

## 📝 Dateien die ich modifiziert habe

- `cloudservice/plugins/example_clock_preview/apps.py` ← Was wichtig ist
- `cloudservice/plugins/example_clock_preview/handlers.py`
- `cloudservice/plugins/example_clock_preview/plugin.json`

**Keine Dateien wurden gelöscht oder fundamental geändert.**

---

## 💡 Hints

- Die `HookRegistry` ist ein **Singleton** - das ist wahrscheinlich das Hauptproblem
- Der `PluginLoader` lädt zur Laufzeit (hot-loading), nicht beim Server-Start
- Imports mit `sys.path` manipulation können tricky sein
- Immer überprüfen dass `clock_preview` im `sys.path` ist

---

**Status morgen wieder checken und diese Schritte durchgehen!** ✅
