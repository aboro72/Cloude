# Beitragen zu Cloude

Vielen Dank für dein Interesse an Cloude! Dieses Dokument erklärt, wie du zum Projekt
beitragen kannst – von der lokalen Entwicklungsumgebung bis zum fertigen Pull Request.

---

## Inhaltsverzeichnis

1. [Verhaltenskodex](#verhaltenskodex)
2. [Voraussetzungen](#voraussetzungen)
3. [Entwicklungsumgebung einrichten](#entwicklungsumgebung-einrichten)
4. [Branch-Strategie](#branch-strategie)
5. [Commit-Konventionen](#commit-konventionen)
6. [Pull Requests](#pull-requests)
7. [Code-Stil](#code-stil)
8. [Tests](#tests)
9. [Sicherheitslücken melden](#sicherheitslücken-melden)
10. [Plugin-Beiträge](#plugin-beiträge)

---

## Verhaltenskodex

Alle Beiträge unterliegen unserem [Verhaltenskodex (Code of Conduct)](CODE_OF_CONDUCT.md).
Durch deine Beteiligung stimmst du zu, diesen einzuhalten.

---

## Voraussetzungen

| Werkzeug | Mindestversion |
|---|---|
| Python | 3.11 |
| Django | 5.x |
| PostgreSQL | 14 (empfohlen) oder SQLite (Entwicklung) |
| Redis | 7 |
| Node.js | 18 (für statische Assets) |
| Git | 2.x |

Stelle sicher, dass du einen freien GitHub-Account hast und das Repository geforkt hast.

---

## Entwicklungsumgebung einrichten

```bash
# 1. Repository klonen (deinen Fork)
git clone https://github.com/<DEIN-USERNAME>/Cloude.git
cd Cloude

# 2. Upstream-Remote hinzufügen
git remote add upstream https://github.com/aboro72/Cloude.git

# 3. Python-Umgebung erstellen
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
.venv\Scripts\activate             # Windows

# 4. Abhängigkeiten installieren
pip install -r requirements.txt

# 5. Umgebungsvariablen einrichten
cp .env.example .env
# .env nach deinen lokalen Werten anpassen (DB, Redis, Secret Key …)

# 6. Datenbankmigrationen ausführen
cd cloudservice
python manage.py migrate

# 7. Statische Dateien sammeln (optional für Entwicklung)
python manage.py collectstatic --noinput

# 8. Entwicklungsserver starten
python manage.py runserver

# Optional: Daphne (WebSocket) parallel starten
daphne -b 0.0.0.0 -p 8001 config.asgi:application
```

> **Tipp:** Für die vollständige Funktionalität (Echtzeit-Benachrichtigungen, Celery-Tasks)
> werden Redis und ein laufender Celery-Worker benötigt:
> ```bash
> celery -A config worker -l info
> celery -A config beat -l info
> ```

---

## Branch-Strategie

```
master          ← Produktions-Branch (nur via PR, keine direkten Pushes)
dev1            ← Haupt-Entwicklungs-Branch (Basis für Feature-Branches)
feature/<name>  ← Neue Features
fix/<name>      ← Bug-Fixes
docs/<name>     ← Dokumentation
security/<name> ← Sicherheitsrelevante Änderungen
```

**Workflow:**

```bash
# Vor jedem neuen Branch: dev1 aktualisieren
git checkout dev1
git pull upstream dev1

# Feature-Branch erstellen
git checkout -b feature/mein-feature

# Arbeit erledigen, committen
git add .
git commit -m "feat: kurze Beschreibung"

# Regelmäßig mit dev1 synchronisieren
git fetch upstream
git rebase upstream/dev1

# Branch pushen und PR erstellen
git push origin feature/mein-feature
```

---

## Commit-Konventionen

Wir verwenden **Conventional Commits** (angelehnt an [conventionalcommits.org](https://www.conventionalcommits.org)):

```
<typ>(<scope>): <kurze Beschreibung>

[optionaler Beschreibungstext]

[optionale Fußzeile(n)]
```

### Typen

| Typ | Bedeutung |
|---|---|
| `feat` | Neues Feature |
| `fix` | Bug-Fix |
| `docs` | Nur Dokumentation |
| `style` | Formatierung, kein Logik-Change |
| `refactor` | Code-Umstrukturierung ohne Funktionsänderung |
| `perf` | Performance-Verbesserung |
| `test` | Tests hinzufügen oder korrigieren |
| `chore` | Build-Prozess, Dependencies, CI |
| `security` | Sicherheitsrelevante Änderungen |

### Beispiele

```bash
git commit -m "feat(messenger): Dateianhänge in Direktnachrichten"
git commit -m "fix(storage): Quota-Check bei Chunk-Upload korrigiert"
git commit -m "security(api): Rate-Limiting auf Public-Links"
git commit -m "docs: CONTRIBUTING.md aktualisiert"
```

---

## Pull Requests

### Checkliste vor dem PR

- [ ] Code läuft lokal ohne Fehler (`python manage.py check`)
- [ ] Migrationen erstellt falls Modelle geändert (`python manage.py makemigrations`)
- [ ] Vorhandene Tests laufen durch (`python manage.py test`)
- [ ] Neue Tests für neue Funktionalität vorhanden
- [ ] Code folgt den [Style-Guidelines](#code-stil)
- [ ] Keine sensiblen Daten (Passwörter, API-Keys) im Code
- [ ] Branch ist auf aktuellem Stand von `dev1` (rebase!)

### PR-Beschreibung

Nutze diese Struktur für den PR-Body:

```markdown
## Was wurde geändert?
Kurze Zusammenfassung der Änderungen.

## Warum?
Kontext: Welches Problem wird gelöst, welches Feature hinzugefügt?

## Wie wurde es getestet?
Beschreibe deine Testschritte.

## Screenshots / Demo (falls UI-Änderungen)
…

## Checkliste
- [ ] Tests vorhanden
- [ ] Dokumentation aktualisiert
- [ ] Breaking Changes dokumentiert
```

### Review-Prozess

1. PRs werden innerhalb von **3–5 Werktagen** geprüft
2. Mindestens **1 Approval** erforderlich bevor Merge
3. CI-Checks müssen grün sein
4. Squash-Merge bevorzugt (saubere History)

---

## Code-Stil

### Python

- **Formatter:** [`black`](https://black.readthedocs.io/) – `black cloudservice/`
- **Linter:** [`flake8`](https://flake8.pycqa.org/) mit `max-line-length = 100`
- **Import-Sortierung:** [`isort`](https://pycli.readthedocs.io/projects/isort/) – `isort cloudservice/`
- **Typ-Annotierungen:** Erwünscht, aber kein Hard-Requirement
- **Docstrings:** Google-Style für öffentliche Klassen und Funktionen

```bash
# Formatter und Linter einmalig installieren
pip install black flake8 isort

# Vor jedem Commit ausführen
black cloudservice/
isort cloudservice/
flake8 cloudservice/ --max-line-length=100
```

### Django-spezifisch

- Views: Klassen-basierte Views (CBVs) bevorzugen
- API-Endpoints: Django REST Framework (DRF) ViewSets
- Permissions: Immer explizit setzen – kein globales `AllowAny`
- Queryset-Filterung: Immer auf den aktuellen Nutzer/Workspace beschränken
- `select_related` / `prefetch_related` bei N+1-Risiko nutzen
- Keine `raw()` SQL-Queries außer bei nachgewiesener Notwendigkeit

### Templates

- Bootstrap 5-Klassen bevorzugen
- Keine Inline-Styles außer für dynamische Werte
- JavaScript: Vanilla JS oder minimale Abhängigkeiten – kein jQuery

---

## Tests

```bash
# Alle Tests ausführen
cd cloudservice
python manage.py test

# Einzelne App testen
python manage.py test storage
python manage.py test api
python manage.py test sharing

# Coverage-Report (pip install coverage)
coverage run manage.py test
coverage report
coverage html  # Öffne htmlcov/index.html im Browser
```

### Was sollte getestet werden?

- **Models:** Validierung, Custom-Methoden, Signale
- **Views:** HTTP-Statuscodes, Permissions, Redirect-Verhalten
- **API:** Serializer, Authentifizierung, Throttling
- **Sharing-Logik:** Token-Validierung, Ablauf-Prüfung, Passwortschutz
- **Upload-Validierung:** Extension-Blocklist, MIME-Type-Prüfung

---

## Sicherheitslücken melden

> **Bitte öffentliche Issues für Sicherheitslücken vermeiden!**

Sicherheitsrelevante Probleme bitte **privat** melden:

1. **E-Mail:** [andreas.borowczak@googlemail.com](mailto:andreas.borowczak@googlemail.com)  
   Betreff: `[SECURITY] Cloude – <kurze Beschreibung>`
2. **GitHub Security Advisory:** [Privates Advisory erstellen](https://github.com/aboro72/Cloude/security/advisories/new)

### Meldung sollte enthalten

- Beschreibung der Schwachstelle
- Schritte zur Reproduktion
- Betroffene Komponente(n) und Version(en)
- Mögliche Auswirkungen (CVSS-Score falls bekannt)
- Optional: Vorgeschlagener Fix

Wir bestätigen den Eingang innerhalb von **48 Stunden** und arbeiten auf eine Lösung in
angemessener Zeit (abhängig von Kritikalität: 7–30 Tage).

---

## Plugin-Beiträge

Cloude verfügt über ein Hook-basiertes Plugin-System. Neue Plugins können als separates
Repository entwickelt und verlinkt werden.

### Anforderungen für offizielle Plugins

- `manifest.json` mit vollständigen Metadaten (Name, Version, Autor, Beschreibung)
- Keine unsanitierten Datenbank-Queries
- Eigene Migrations im Plugin-Verzeichnis
- Dokumentation im Plugin-eigenen `README.md`
- Tests für die Kernfunktionalität
- Kein dynamisches `importlib`-Laden von externem Code innerhalb des Plugins

### Plugin-Struktur

```
plugins/installed/mein_plugin/
├── __init__.py
├── manifest.json       # Pflicht
├── apps.py
├── models.py           # Falls Datenbankmodelle benötigt
├── views.py
├── urls.py
├── hooks.py            # Plugin-Hooks registrieren
├── templates/
│   └── mein_plugin/
├── static/
│   └── mein_plugin/
├── migrations/
└── README.md
```

Für Fragen zur Plugin-Entwicklung bitte ein Issue mit dem Label `plugin-dev` erstellen.

---

## Lizenz

Mit dem Einreichen eines Beitrags stimmst du zu, dass dein Beitrag unter der gleichen Lizenz
wie das Projekt veröffentlicht wird. Details findest du in der [LICENSE](LICENSE)-Datei.

---

*Cloude – entwickelt von [Andreas Borowczak](https://aborosoft.com) | AboroSoft*
