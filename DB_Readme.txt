MongoDB Zugangsdaten

Host: 212.44.166.234
Port: 27017
Datenbank: cloudservice
Auth-DB: cloudservice

DB-Admin fuer Anwendung:
Benutzername: cloudservice_admin
Passwort: wybCihs9B473VFfVhddnt8tq1vte

Hinweis:
Der Benutzer hat Rollen fuer readWrite, dbAdmin und userAdmin auf der Datenbank cloudservice.

Projektkonfiguration:
Die MongoDB-Zugangsdaten sind zusaetzlich in .env fuer Django/pymongo hinterlegt.
Verbindungstest im Projekt:
.\.venv\Scripts\python.exe cloudservice\manage.py mongodb_ping

Hinweis zum URI:
Verwende wegen fehlender TLS-Unterstuetzung auf der Plattform die explizit formulierte URI mit `?tls=false`, wie oben in .env dokumentiert. MongoDB Compass nutzt dieselbe Zeichenkette, deshalb funktioniert dort die Verbindung trotz der lokalen Firewall-Einstellung.

Geplanter DB-Admin (noch nicht erstellt):
Datum: 2026-04-11
Host: 212.44.166.234
Port: 27017
Datenbank: cloudservice
Auth-DB: cloudservice
Benutzername: dbadmin
Passwort: 0w70KSfFfzZQW220Mkejpct4
Hinweis: Die neue Datenbank und der Admin wurden hier dokumentiert, damit das Provisioning gegen den externen MongoDB-Host nachvollziehbar ist.
