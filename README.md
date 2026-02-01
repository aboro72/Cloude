# CloudService

Ein moderner Cloud-Speicherdienst entwickelt mit Django 5.x und Bootstrap 5.

**Entwickelt von Andreas Borowczak | [Aboro IT](https://aboro-it.de)**

---

## Inhaltsverzeichnis

1. [Features](#features)
2. [Systemanforderungen](#systemanforderungen)
3. [Schnellinstallation](#schnellinstallation)
4. [Installation ISPConfig3 + Nginx](#installation-ispconfig3--nginx)
5. [Installation ISPConfig3 + Apache2](#installation-ispconfig3--apache2)
6. [Installation Standalone Nginx](#installation-standalone-nginx)
7. [Installation Standalone Apache2](#installation-standalone-apache2)
8. [Docker Installation](#docker-installation)
9. [Konfiguration](#konfiguration)
10. [Plugin-System](#plugin-system)
11. [Troubleshooting](#troubleshooting)

---

## Features

- **Dateiverwaltung**: Upload, Download, Verschieben, Umbenennen
- **Ordnerstruktur**: Hierarchische Ordner mit Breadcrumb-Navigation
- **Dateivorschau**: Bilder, Videos, Audio, PDFs direkt im Browser
- **Versionierung**: Automatische Dateiversionen mit Wiederherstellung
- **Papierkorb**: Soft-Delete mit Wiederherstellung
- **Freigaben**: Oeffentliche Links mit Passwortschutz und Ablaufdatum
- **Plugin-System**: Erweiterbar durch Hook-basierte Plugins
- **Responsive Design**: Optimiert fuer Desktop und Mobile

---

## Systemanforderungen

- Python 3.10+
- Django 5.0+
- SQLite3 / PostgreSQL / MySQL
- 512 MB RAM (minimum)
- 1 GB Festplattenspeicher

---

## Schnellinstallation

```bash
# Repository klonen
git clone https://github.com/aboro-it/cloudservice.git
cd cloudservice

# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Abhaengigkeiten installieren
pip install -r requirements.txt

# Datenbank initialisieren
cd cloudservice
python manage.py migrate

# Superuser erstellen
python manage.py createsuperuser

# Entwicklungsserver starten
python manage.py runserver
```

Zugriff: http://localhost:8000

---

## Installation ISPConfig3 + Nginx

### 1. Website in ISPConfig anlegen

1. ISPConfig Panel oeffnen -> Sites -> Websites -> Add new website
2. Einstellungen:
   - Domain: `cloud.beispiel.de`
   - PHP: `Disabled` (wir nutzen Python)
   - Python: `Enabled`
   - SSL: `Let's Encrypt`

### 2. Anwendung einrichten

```bash
# Als Web-User einloggen
su - web1

# In Website-Verzeichnis wechseln
cd /var/www/cloud.beispiel.de/web

# Repository klonen
git clone https://github.com/aboro-it/cloudservice.git .

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate

# Abhaengigkeiten installieren
pip install -r requirements.txt
pip install gunicorn

# Umgebungsvariablen
cp cloudservice/.env.example cloudservice/.env
nano cloudservice/.env
```

### 3. .env Konfiguration

```env
DEBUG=False
SECRET_KEY=dein-sehr-langer-geheimer-schluessel-hier
ALLOWED_HOSTS=cloud.beispiel.de
DATABASE_URL=sqlite:///db.sqlite3

# Fuer PostgreSQL:
# DATABASE_URL=postgres://user:password@localhost:5432/cloudservice
```

### 4. Anwendung initialisieren

```bash
cd cloudservice
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 5. Gunicorn Service erstellen

```bash
sudo nano /etc/systemd/system/cloudservice.service
```

```ini
[Unit]
Description=CloudService Gunicorn Daemon
After=network.target

[Service]
User=web1
Group=client1
WorkingDirectory=/var/www/cloud.beispiel.de/web/cloudservice
Environment="PATH=/var/www/cloud.beispiel.de/web/venv/bin"
ExecStart=/var/www/cloud.beispiel.de/web/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/var/www/cloud.beispiel.de/web/cloudservice.sock \
    config.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudservice
sudo systemctl start cloudservice
```

### 6. Nginx Konfiguration (ISPConfig)

In ISPConfig -> Sites -> Website -> Options -> Nginx Directives:

```nginx
location /static/ {
    alias /var/www/cloud.beispiel.de/web/cloudservice/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

location /media/ {
    alias /var/www/cloud.beispiel.de/web/cloudservice/media/;
    expires 7d;
}

location / {
    proxy_pass http://unix:/var/www/cloud.beispiel.de/web/cloudservice.sock;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 300s;
    proxy_read_timeout 300s;
    client_max_body_size 100M;
}
```

### 7. Dienst neustarten

```bash
sudo systemctl restart nginx
sudo systemctl restart cloudservice
```

---

## Installation ISPConfig3 + Apache2

### 1. Website in ISPConfig anlegen

1. ISPConfig Panel -> Sites -> Websites -> Add new website
2. Einstellungen:
   - Domain: `cloud.beispiel.de`
   - PHP: `Disabled`
   - SSL: `Let's Encrypt`

### 2. Anwendung einrichten

```bash
su - web1
cd /var/www/cloud.beispiel.de/web

git clone https://github.com/aboro-it/cloudservice.git .
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install gunicorn

cp cloudservice/.env.example cloudservice/.env
nano cloudservice/.env

cd cloudservice
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 3. Gunicorn Service erstellen

```bash
sudo nano /etc/systemd/system/cloudservice.service
```

```ini
[Unit]
Description=CloudService Gunicorn Daemon
After=network.target

[Service]
User=web1
Group=client1
WorkingDirectory=/var/www/cloud.beispiel.de/web/cloudservice
Environment="PATH=/var/www/cloud.beispiel.de/web/venv/bin"
ExecStart=/var/www/cloud.beispiel.de/web/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    config.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudservice
sudo systemctl start cloudservice
```

### 4. Apache Module aktivieren

```bash
sudo a2enmod proxy proxy_http headers
sudo systemctl restart apache2
```

### 5. Apache Konfiguration (ISPConfig)

In ISPConfig -> Sites -> Website -> Options -> Apache Directives:

```apache
ProxyPreserveHost On
ProxyPass /static/ !
ProxyPass /media/ !

Alias /static/ /var/www/cloud.beispiel.de/web/cloudservice/staticfiles/
Alias /media/ /var/www/cloud.beispiel.de/web/cloudservice/media/

<Directory /var/www/cloud.beispiel.de/web/cloudservice/staticfiles>
    Require all granted
    Options -Indexes
</Directory>

<Directory /var/www/cloud.beispiel.de/web/cloudservice/media>
    Require all granted
    Options -Indexes
</Directory>

ProxyPass / http://127.0.0.1:8000/
ProxyPassReverse / http://127.0.0.1:8000/

<Proxy *>
    Require all granted
</Proxy>

# Upload-Limit
LimitRequestBody 104857600
```

### 6. Dienste neustarten

```bash
sudo systemctl restart apache2
sudo systemctl restart cloudservice
```

---

## Installation Standalone Nginx

### 1. System vorbereiten

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx git

# CentOS/RHEL
sudo yum install python3 python3-pip nginx git
```

### 2. Benutzer erstellen

```bash
sudo useradd -m -s /bin/bash cloudservice
sudo su - cloudservice
```

### 3. Anwendung installieren

```bash
cd /home/cloudservice
git clone https://github.com/aboro-it/cloudservice.git
cd cloudservice

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install gunicorn

cp cloudservice/.env.example cloudservice/.env
nano cloudservice/.env
```

### 4. .env konfigurieren

```env
DEBUG=False
SECRET_KEY=generiere-einen-sicheren-schluessel
ALLOWED_HOSTS=cloud.beispiel.de,www.cloud.beispiel.de
DATABASE_URL=sqlite:///db.sqlite3
```

### 5. Anwendung initialisieren

```bash
cd cloudservice
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
exit  # Zurueck zu root
```

### 6. Gunicorn Service

```bash
sudo nano /etc/systemd/system/cloudservice.service
```

```ini
[Unit]
Description=CloudService Gunicorn Daemon
After=network.target

[Service]
User=cloudservice
Group=cloudservice
WorkingDirectory=/home/cloudservice/cloudservice/cloudservice
Environment="PATH=/home/cloudservice/cloudservice/venv/bin"
ExecStart=/home/cloudservice/cloudservice/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/cloudservice/cloudservice/cloudservice.sock \
    config.wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudservice
sudo systemctl start cloudservice
```

### 7. Nginx Konfiguration

```bash
sudo nano /etc/nginx/sites-available/cloudservice
```

```nginx
server {
    listen 80;
    server_name cloud.beispiel.de;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name cloud.beispiel.de;

    # SSL-Zertifikate (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/cloud.beispiel.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cloud.beispiel.de/privkey.pem;

    # SSL-Einstellungen
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Maximale Upload-Groesse
    client_max_body_size 100M;

    # Statische Dateien
    location /static/ {
        alias /home/cloudservice/cloudservice/cloudservice/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media-Dateien
    location /media/ {
        alias /home/cloudservice/cloudservice/cloudservice/media/;
        expires 7d;
    }

    # Anwendung
    location / {
        proxy_pass http://unix:/home/cloudservice/cloudservice/cloudservice.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### 8. Aktivieren und starten

```bash
sudo ln -s /etc/nginx/sites-available/cloudservice /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 9. SSL-Zertifikat (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d cloud.beispiel.de
```

---

## Installation Standalone Apache2

### 1. System vorbereiten

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv apache2 git
sudo a2enmod proxy proxy_http ssl headers

# CentOS/RHEL
sudo yum install python3 python3-pip httpd mod_ssl git
```

### 2. Benutzer und Anwendung

```bash
sudo useradd -m -s /bin/bash cloudservice
sudo su - cloudservice

cd /home/cloudservice
git clone https://github.com/aboro-it/cloudservice.git
cd cloudservice

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install gunicorn

cp cloudservice/.env.example cloudservice/.env
nano cloudservice/.env

cd cloudservice
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
exit
```

### 3. Gunicorn Service

```bash
sudo nano /etc/systemd/system/cloudservice.service
```

```ini
[Unit]
Description=CloudService Gunicorn Daemon
After=network.target

[Service]
User=cloudservice
Group=cloudservice
WorkingDirectory=/home/cloudservice/cloudservice/cloudservice
Environment="PATH=/home/cloudservice/cloudservice/venv/bin"
ExecStart=/home/cloudservice/cloudservice/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    config.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudservice
sudo systemctl start cloudservice
```

### 4. Apache VirtualHost

```bash
sudo nano /etc/apache2/sites-available/cloudservice.conf
```

```apache
<VirtualHost *:80>
    ServerName cloud.beispiel.de
    Redirect permanent / https://cloud.beispiel.de/
</VirtualHost>

<VirtualHost *:443>
    ServerName cloud.beispiel.de

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/cloud.beispiel.de/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/cloud.beispiel.de/privkey.pem

    # Statische Dateien
    Alias /static/ /home/cloudservice/cloudservice/cloudservice/staticfiles/
    Alias /media/ /home/cloudservice/cloudservice/cloudservice/media/

    <Directory /home/cloudservice/cloudservice/cloudservice/staticfiles>
        Require all granted
        Options -Indexes
    </Directory>

    <Directory /home/cloudservice/cloudservice/cloudservice/media>
        Require all granted
        Options -Indexes
    </Directory>

    # Proxy zum Gunicorn
    ProxyPreserveHost On
    ProxyPass /static/ !
    ProxyPass /media/ !
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # Upload-Limit (100MB)
    LimitRequestBody 104857600

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/cloudservice-error.log
    CustomLog ${APACHE_LOG_DIR}/cloudservice-access.log combined
</VirtualHost>
```

### 5. Aktivieren

```bash
sudo a2ensite cloudservice.conf
sudo apache2ctl configtest
sudo systemctl restart apache2
```

### 6. SSL-Zertifikat

```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d cloud.beispiel.de
```

---

## Docker Installation

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgres://postgres:postgres@db:5432/cloudservice
    volumes:
      - static_data:/app/staticfiles
      - media_data:/app/media
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=cloudservice
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - static_data:/app/staticfiles
      - media_data:/app/media
    depends_on:
      - web

volumes:
  postgres_data:
  static_data:
  media_data:
```

### Starten

```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

---

## Konfiguration

### Umgebungsvariablen (.env)

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `DEBUG` | Debug-Modus | `True` |
| `SECRET_KEY` | Django Secret Key | Generiert |
| `ALLOWED_HOSTS` | Erlaubte Domains | `localhost` |
| `DATABASE_URL` | Datenbank-URL | SQLite |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | Max. Upload-Groesse | 100MB |
| `MEDIA_ROOT` | Medien-Verzeichnis | `media/` |
| `STATIC_ROOT` | Statische Dateien | `staticfiles/` |

### Datenbankoptionen

**SQLite (Standard):**
```env
DATABASE_URL=sqlite:///db.sqlite3
```

**PostgreSQL:**
```env
DATABASE_URL=postgres://user:password@localhost:5432/cloudservice
```

**MySQL:**
```env
DATABASE_URL=mysql://user:password@localhost:3306/cloudservice
```

---

## Plugin-System

CloudService unterstuetzt ein Hook-basiertes Plugin-System.

### Plugin aktivieren

1. Plugin in `plugins/installed/` ablegen
2. Admin-Panel -> Plugins -> Plugin aktivieren

### Verfuegbare Hooks

- `UI_DASHBOARD_WIDGET` - Dashboard-Widgets
- `UI_NAVBAR_ITEM` - Navigationseintraege
- `STORAGE_FILE_UPLOAD` - Upload-Verarbeitung
- `STORAGE_FILE_DOWNLOAD` - Download-Verarbeitung

---

## Troubleshooting

### Allgemeine Probleme

#### 502 Bad Gateway

**Ursache:** Gunicorn laeuft nicht oder Socket-Berechtigung fehlt.

```bash
# Status pruefen
sudo systemctl status cloudservice

# Logs anzeigen
sudo journalctl -u cloudservice -n 50

# Neustart
sudo systemctl restart cloudservice
```

#### Static/Media Files werden nicht geladen

**Ursache:** Falsche Pfade oder Berechtigungen.

```bash
# collectstatic ausfuehren
python manage.py collectstatic --noinput

# Berechtigungen pruefen
ls -la staticfiles/
ls -la media/

# Nginx/Apache Konfiguration pruefen
sudo nginx -t
# oder
sudo apache2ctl configtest
```

#### Bilder/Videos werden nicht angezeigt

**Ursache:** Media-URL nicht konfiguriert oder Dateiberechtigungen.

```bash
# Pruefen ob Datei existiert
ls -la media/files/

# Berechtigungen korrigieren
sudo chown -R www-data:www-data media/
# oder fuer ISPConfig:
sudo chown -R web1:client1 media/
```

#### Upload schlaegt fehl (413 Entity Too Large)

**Nginx:**
```nginx
client_max_body_size 100M;
```

**Apache:**
```apache
LimitRequestBody 104857600
```

### Datenbankprobleme

#### Migrations-Fehler

```bash
# Migrations zuruecksetzen
python manage.py migrate --fake-initial

# Neue Migration erstellen
python manage.py makemigrations
python manage.py migrate
```

#### Datenbank-Lock (SQLite)

```bash
# Prozesse pruefen
fuser db.sqlite3

# Prozess beenden
kill <PID>
```

### Gunicorn-Probleme

#### Worker Timeout

In `/etc/systemd/system/cloudservice.service`:
```ini
ExecStart=/path/to/gunicorn \
    --workers 3 \
    --timeout 120 \
    --bind unix:/path/to/cloudservice.sock \
    config.wsgi:application
```

#### Socket-Berechtigungen

```bash
# Socket-Pfad pruefen
ls -la /path/to/cloudservice.sock

# Berechtigungen in Service-Datei:
ExecStart=/path/to/gunicorn \
    --workers 3 \
    --bind unix:/path/to/cloudservice.sock \
    --umask 0000 \
    config.wsgi:application
```

### SSL-Probleme

#### Let's Encrypt Zertifikat erneuern

```bash
sudo certbot renew --dry-run
sudo certbot renew
```

#### Mixed Content Fehler

In Django settings:
```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
```

### Log-Dateien

```bash
# Django/Gunicorn
sudo journalctl -u cloudservice -f

# Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Apache
sudo tail -f /var/log/apache2/cloudservice-error.log
sudo tail -f /var/log/apache2/cloudservice-access.log
```

### Performance-Optimierung

#### Gunicorn Workers

Faustregel: `(2 x CPU-Kerne) + 1`

```ini
ExecStart=/path/to/gunicorn \
    --workers 5 \
    --threads 2 \
    --bind unix:/path/to/cloudservice.sock \
    config.wsgi:application
```

#### Nginx Caching

```nginx
location /static/ {
    alias /path/to/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
    gzip on;
    gzip_types text/css application/javascript;
}
```

---

## Support

- **Issues:** [GitHub Issues](https://github.com/aboro-it/cloudservice/issues)
- **Entwickler:** Andreas Borowczak
- **Unternehmen:** [Aboro IT](https://aboro-it.de)

---

## Lizenz

MIT License - siehe [LICENSE](LICENSE) fuer Details.
