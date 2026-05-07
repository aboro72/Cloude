# Hand-off: Abteilungen ↔ Team-Sites ↔ News

Stand: 2026-05-07

## Ziel

- Auf einer Abteilungsseite Team-Sites **zuweisen** und **direkt erstellen**.
- Aus dem Abteilungs-Kontext **News** für Team-Sites erstellen.
- Wenn eine Team-Site einer Abteilung zugewiesen wird, bekommen Abteilungsleitung/Manager automatisch die nötigen Rollen (und beim Entfernen werden nur die *auto*-Rollen wieder entfernt).

## Relevante Änderungen (Code)

- Department → Team-Site Zuweisen/Unassign + Auto-Rollen:
  - `cloudservice/departments/views.py`
    - Helper: `_sync_department_leaders_to_team_site(dept, site)`
    - Assign: Auto-Add + Tracking
    - Unassign: Entfernt nur *auto-added* User (keine manuell hinzugefügten)

- Team-Site „aus Abteilung heraus“ erstellen (Auto-Zuweisung + Auto-Rollen):
  - `cloudservice/sharing/views.py`
    - `CreateGroupView` akzeptiert `?department=<department-slug>`
    - Setzt `GroupShare.department`
    - Auto-Add von Department-Head/Managern als `members` + `team_leaders` (mit Tracking)

- Tracking-Modell + Migration für Auto-Rollen:
  - `cloudservice/sharing/models.py`
    - `GroupShareDepartmentAutoRole`
  - `cloudservice/sharing/migrations/0009_groupshare_department_auto_role.py`

- UI/Buttons:
  - Department Detail: `cloudservice/templates/departments/detail.html`
    - Buttons „Neue Team-Site“, „Zuweisen“
    - Pro Team-Site (wenn managebar) „News“ / „News erstellen“
    - Im News-Block optionaler „News erstellen“-Button/Dropdown
  - Team-Sites zuweisen: `cloudservice/templates/departments/assign_sites.html`
    - Button „Neue Team-Site“ (mit `?department=<slug>`)
  - Team-Site Create Page Hinweis/Back-Link: `cloudservice/templates/sharing/create_group.html`

## Migration-Konflikt in `accounts` (Fix)

Beim Ausführen von `migrate` gab es:

> Conflicting migrations detected; multiple leaf nodes: (0007_must_change_password, 0007_userprofile_must_change_password)

Fix (bereits im Repo):

- `cloudservice/accounts/migrations/0007_userprofile_must_change_password.py` ist jetzt No-Op und hängt von `0007_must_change_password` ab.
- Merge-Migration: `cloudservice/accounts/migrations/0008_merge_0007_must_change_password.py`

Falls noch nicht passiert, einmal ausführen:

```powershell
cd cloudservice
python manage.py migrate accounts
```

## Datenbank-Hinweis (MySQL vs. SQLite)

In dieser Umgebung wurde tatsächlich MySQL genutzt:

- `ENGINE=django.db.backends.mysql`
- DB: `ml-storage`

Wenn Login-Passwörter „plötzlich nicht mehr passen“, ist es sehr oft so, dass man vorher gegen SQLite (`db.sqlite3`) gearbeitet hat und jetzt gegen MySQL (andere User-Tabelle/Hashes).

Passwort reset (falls nötig):

```powershell
cd cloudservice
python manage.py changepassword <username>
```

## Wichtige URLs zum Testen

- Department: `http://127.0.0.1:8000/departments/Entwicklung/`
- Team-Sites zuweisen: `http://127.0.0.1:8000/departments/Entwicklung/team-sites/`

Test-Checkliste:

1) Team-Site zuweisen → Department-Leitung/Manager sehen die Site und können News anlegen.
2) Team-Site unassignen → *nur* auto-hinzugefügte Member/Leader werden entfernt; manuelle bleiben.
3) „Neue Team-Site“ aus Abteilung → Site landet direkt in der Abteilung + Rollen werden gesetzt.

