# Fortsetzungs-Prompt für Codex – Meetings-Feature

## Was wurde bereits implementiert (vollständig fertig)

### Neue Dateien:
- `cloudservice/jitsi/models.py` – `Meeting`-Model mit Status (planned/running/ended/cancelled),
  Feldern für organizer, invitees (M2M), scheduled_start/end, room_name (erst beim Start gesetzt),
  started_at, ended_at, Methoden: start(), end(), cancel(), duration_display, can_be_*_by()
- `cloudservice/jitsi/admin.py` – MeetingAdmin registriert
- `cloudservice/jitsi/migrations/0001_initial.py` – Migration erstellt + angewendet (OK)

### Geänderte Dateien:
- `cloudservice/jitsi/views.py` – Neue Views: meetings(), schedule(), start_meeting(),
  join_meeting(), end_meeting(), cancel_meeting(). Alte join/token_api behalten.
- `cloudservice/jitsi/urls.py` – Neue URL-Patterns für alle neuen Views
- `cloudservice/templates/jitsi/meetings.html` – Komplett neu: zeigt laufende/geplante/
  vergangene Meetings mit Karten-Layout, Schedule-Modal mit Eingeladenen-Chips

### accounts/0007-Migration:
- Wurde auto-generiert (must_change_password schon in DB) → wurde mit --fake markiert, kein Problem

## Was noch fehlen könnte / nächste Schritte

1. **Benachrichtigung via Messenger**: Wenn ein Meeting geplant wird, könnte eine Systemnachricht
   in einem gemeinsamen DM-Raum oder Kanal der Eingeladenen landen.
   - Dafür `messenger.models.ChatRoom`, `ChatMessage` importieren
   - In `schedule()`-View nach `meeting.invitees.set(...)` für jeden Eingeladenen
     prüfen ob ein DM-Raum existiert → ChatMessage erstellen
   - Oder alternativ: Email-Benachrichtigung

2. **Sofortiger Start** (ohne Planung): Button "Jetzt starten" auf der Meetings-Seite startet
   sofort ein Meeting ohne scheduled_start. Das geht schon über den alten `join`-View, könnte
   aber als echtes Meeting-Objekt angelegt werden für die Historie.

3. **iCal / Kalender-Export**: Meeting als .ics-Datei exportieren für externe Kalender

4. **README.md aktualisieren**: Meetings-Feature beschreiben

## Datei-Übersicht

```
cloudservice/
├── jitsi/
│   ├── models.py      ← NEU
│   ├── admin.py       ← NEU
│   ├── views.py       ← GEÄNDERT
│   ├── urls.py        ← GEÄNDERT
│   └── migrations/
│       └── 0001_initial.py  ← NEU + APPLIED
└── templates/jitsi/
    └── meetings.html  ← KOMPLETT NEU
```

## Wichtige Konventionen im Projekt

- Venv: `/home/storage/Cloude/venv/bin/python`
- DB: MySQL (pymysql)
- Firmen-Kontext: `request.user.profile.company` → `Company`-Model
- Jitsi-URL: `settings.JITSI_URL` (default: https://meet.aborosoft.com)
- JWT via `settings.JITSI_APP_ID` + `JITSI_APP_SECRET`
- Templates: `{% extends "base.html" %}`, Bootstrap 5 + Bootstrap Icons (`bi bi-*`)
