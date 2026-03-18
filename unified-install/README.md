# Django Platform - Docker-Compose Installation

Complete Docker setup for **Cloude** (Cloud Storage) and **HelpDesk** (Support Ticketing) on shared MariaDB with SSO.

## Quick Start

### Prerequisites

- **Docker** 20.10+ ([Install](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ ([Install](https://docs.docker.com/compose/install/))
- **Git** (optional, for version control)
- **3 GB RAM** minimum (5+ GB recommended)
- **10 GB disk** space minimum

### Linux / macOS

```bash
cd unified-install
chmod +x setup.sh
./setup.sh
```

### Windows (PowerShell)

```powershell
cd unified-install
.\setup.bat
```

## Manual Installation

If you prefer manual setup:

### 1. Copy environment template

```bash
cp .env.example .env
```

### 2. Edit .env with your settings

```bash
nano .env  # Linux/macOS
notepad .env  # Windows
```

Key variables to customize:
- `DB_ROOT_PASSWORD` - MariaDB root password
- `DB_PASSWORD` - Application database user password
- `JWT_SECRET_KEY` - JWT signing key (must be same for all apps)
- `SSO_COOKIE_DOMAIN` - For subdomain SSO (e.g., `.yourdomain.com`)
- `CLOUDE_ALLOWED_HOSTS` / `HELPDESK_ALLOWED_HOSTS` - Your domain names

### 3. Start services

```bash
docker-compose up -d
```

### 4. Run migrations

**Cloude:**
```bash
docker-compose exec cloude_web python manage.py migrate
```

**HelpDesk:**
```bash
docker-compose exec helpdesk_web python manage.py migrate
```

### 5. Create superuser accounts

**Cloude:**
```bash
docker-compose exec cloude_web python manage.py createsuperuser
```

**HelpDesk:**
```bash
docker-compose exec helpdesk_web python manage.py createsuperuser
```

### 6. Access applications

**Cloude:** http://cloude.localhost (or your domain)
**HelpDesk:** http://helpdesk.localhost (or your domain)

## Configuration Options

### Deployment Modes

#### Subdomain-Based (Recommended for production)

Good for: Multiple domains, SSL per domain

```
cloude.yourdomain.com
helpdesk.yourdomain.com
```

**Configuration:**
```env
SSO_COOKIE_DOMAIN=.yourdomain.com
CLOUDE_ALLOWED_HOSTS=cloude.yourdomain.com,yourdomain.com
HELPDESK_ALLOWED_HOSTS=helpdesk.yourdomain.com,support.yourdomain.com
```

#### Path-Based

Good for: Single domain, simplified setup

```
yourdomain.com/cloude
yourdomain.com/helpdesk
```

**Note:** Requires additional Nginx configuration (see `nginx/conf.d/platform-paths.conf`)

#### Port-Based

Good for: Development, multiple independent instances

```
yourdomain.com:8000 (Cloude)
yourdomain.com:8100 (HelpDesk)
```

### Environment Variables

**Database**
- `DB_ROOT_PASSWORD` - MariaDB root password
- `DB_USER` - Database user (default: platform_user)
- `DB_PASSWORD` - Database user password

**JWT/SSO**
- `JWT_SECRET_KEY` - Must be identical across all apps
- `SSO_COOKIE_DOMAIN` - Domain for cross-app authentication
- `SSO_COOKIE_SECURE` - Use secure cookies (set to True in production)

**Cloude**
- `CLOUDE_DEBUG` - Debug mode (set to False in production)
- `CLOUDE_SECRET_KEY` - Django secret key
- `CLOUDE_ALLOWED_HOSTS` - Allowed hostnames

**HelpDesk**
- `HELPDESK_DEBUG` - Debug mode (set to False in production)
- `HELPDESK_SECRET_KEY` - Django secret key
- `HELPDESK_ALLOWED_HOSTS` - Allowed hostnames

**Email**
- `EMAIL_HOST` - SMTP server
- `EMAIL_PORT` - SMTP port (usually 587)
- `EMAIL_HOST_USER` - Email username
- `EMAIL_HOST_PASSWORD` - Email password

See `.env.example` for all available options.

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Nginx (Reverse Proxy)                   │
├────────────────────────┬────────────────────────────────────┤
│      Cloude            │        HelpDesk                     │
├────────────────────────┼────────────────────────────────────┤
│  ┌──────────────────┐  │  ┌──────────────────┐              │
│  │  Django Web      │  │  │  Django Web      │              │
│  │  (Gunicorn)      │  │  │  (Gunicorn)      │              │
│  └──────────────────┘  │  └──────────────────┘              │
│  ┌──────────────────┐  │  ┌──────────────────┐              │
│  │  Daphne          │  │  │  (Not needed)    │              │
│  │  (WebSockets)    │  │  └──────────────────┘              │
│  └──────────────────┘  │                                     │
│  ┌──────────────────┐  │  ┌──────────────────┐              │
│  │  Celery Worker   │  │  │  Celery Worker   │              │
│  └──────────────────┘  │  └──────────────────┘              │
│  ┌──────────────────┐  │  ┌──────────────────┐              │
│  │  Celery Beat     │  │  │  Celery Beat     │              │
│  └──────────────────┘  │  └──────────────────┘              │
│  ┌──────────────────┐  │  ┌──────────────────┐              │
│  │  Redis           │  │  │  Redis           │              │
│  │  (Cache/Broker)  │  │  │  (Cache/Broker)  │              │
│  └──────────────────┘  │  └──────────────────┘              │
├────────────────────────┼────────────────────────────────────┤
│                    MariaDB (Shared)                          │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │  platform_auth   │  │  cloude_db       │  │helpdesk_db │ │
│  │  (Users/Auth)    │  │  (Storage Data)  │  │(Tickets)   │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Common Commands

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f cloude_web
docker-compose logs -f helpdesk_web
```

### Stop services

```bash
docker-compose down
```

### Stop and remove volumes (WARNING: deletes data!)

```bash
docker-compose down -v
```

### Restart services

```bash
docker-compose restart
```

### Execute commands in container

```bash
# Run Django management command
docker-compose exec cloude_web python manage.py migrate

# Interactive shell
docker-compose exec cloude_web bash
docker-compose exec -T cloude_web python manage.py shell
```

### View database

```bash
docker-compose exec mariadb mysql -uroot -p$DB_ROOT_PASSWORD
```

## Troubleshooting

### Port already in use

If port 80, 443, 3306, etc. are in use:

**Edit docker-compose.yml:**
```yaml
ports:
  - "8080:80"  # Change from 80:80 to 8080:80
```

### Database connection errors

Check MariaDB logs:
```bash
docker-compose logs mariadb
```

Ensure database is healthy:
```bash
docker-compose exec mariadb mysqladmin ping -h localhost
```

### Unable to login

Verify user was created:
```bash
docker-compose exec mariadb mysql -uroot -p$DB_ROOT_PASSWORD platform_auth

SELECT * FROM platform_users;
```

### Permission denied on setup script (Linux/macOS)

```bash
chmod +x setup.sh
./setup.sh
```

### Docker image build fails

Clear cache and rebuild:
```bash
docker-compose build --no-cache
```

## Production Deployment

For production, ensure:

1. **Security**
   - [ ] Change all passwords in `.env`
   - [ ] Set `DEBUG=False` for both apps
   - [ ] Generate new `SECRET_KEY` and `JWT_SECRET_KEY`
   - [ ] Use HTTPS (configure SSL certificates in Nginx)

2. **Database**
   - [ ] Use strong passwords
   - [ ] Enable database backups
   - [ ] Configure database persistence volumes

3. **Monitoring**
   - [ ] Set up log aggregation
   - [ ] Configure health checks
   - [ ] Monitor disk space and memory usage

4. **Backups**
   ```bash
   # Backup database
   docker-compose exec mariadb mysqldump -uroot -p$DB_ROOT_PASSWORD --all-databases > backup.sql

   # Backup volumes
   docker run --rm -v mariadb_data:/data -v $(pwd):/backup \
     alpine tar czf /backup/mariadb_backup.tar.gz /data
   ```

## Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Review [MIGRATION_GUIDE_HELPDESK.md](../MIGRATION_GUIDE_HELPDESK.md)
3. Check `.env` configuration
4. Verify ports are not in use: `netstat -an | grep LISTEN`

## License

Same as parent projects (Cloude and HelpDesk)
