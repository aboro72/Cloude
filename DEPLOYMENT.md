# CloudService - Production Deployment Guide

Comprehensive guide for deploying CloudService to production.

## 🚀 Pre-Deployment Checklist

### Security
- [ ] Change `SECRET_KEY` to a secure value
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Enable `SECURE_SSL_REDIRECT`
- [ ] Enable `SESSION_COOKIE_SECURE`
- [ ] Enable `CSRF_COOKIE_SECURE`
- [ ] Generate SSL certificates (Let's Encrypt)
- [ ] Set strong database password
- [ ] Set strong Redis password
- [ ] Configure email backend properly

### Infrastructure
- [ ] Set up PostgreSQL server (managed or self-hosted)
- [ ] Set up Redis server (managed or self-hosted)
- [ ] Configure DNS records
- [ ] Set up backups (automated daily)
- [ ] Configure monitoring and alerts
- [ ] Set up log aggregation

### Application
- [ ] Run tests locally: `pytest`
- [ ] Check code quality: `flake8`, `black`
- [ ] Review security: `bandit`
- [ ] Update dependencies: `pip install --upgrade -r requirements.txt`
- [ ] Test database migrations on staging
- [ ] Load test the application

## 📋 Deployment Steps

### 1. Prepare Server

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y python3.11 python3.11-venv \
    postgresql postgresql-contrib postgresql-client \
    redis-server redis-tools \
    nginx supervisor git curl

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

### 2. Clone Repository

```bash
# Clone repository
git clone https://github.com/yourusername/cloudservice.git
cd cloudservice

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env

# Key settings for production:
DEBUG=False
SECRET_KEY=<generate-with-django>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DATABASE_URL=postgresql://user:password@localhost:5432/cloudservice
REDIS_URL=redis://:password@localhost:6379/0
```

### 4. Database Setup

```bash
# Create PostgreSQL user and database
sudo -u postgres psql << EOF
CREATE USER cloudservice_user WITH PASSWORD 'your-secure-password';
CREATE DATABASE cloudservice OWNER cloudservice_user;
GRANT ALL PRIVILEGES ON DATABASE cloudservice TO cloudservice_user;
ALTER ROLE cloudservice_user SET client_encoding TO 'utf8';
ALTER ROLE cloudservice_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE cloudservice_user SET default_transaction_deferrable TO on;
ALTER ROLE cloudservice_user SET default_transaction_isolation TO 'read committed';
EOF

# Run migrations
python cloudservice/manage.py migrate

# Create superuser
python cloudservice/manage.py createsuperuser

# Collect static files
python cloudservice/manage.py collectstatic --noinput
```

### 5. SSL Certificate Setup

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate from Let's Encrypt
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Update nginx.conf with SSL settings
# Uncomment SSL section and update paths
```

### 6. Nginx Configuration

```bash
# Copy and edit nginx config
sudo cp nginx.conf /etc/nginx/nginx.conf
sudo nano /etc/nginx/nginx.conf

# Test configuration
sudo nginx -t

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 7. Supervisor Configuration

```bash
# Create supervisor config
sudo nano /etc/supervisor/conf.d/cloudservice.conf
```

Add the following:

```ini
[program:cloudservice]
directory=/path/to/cloudservice/cloudservice
command=/path/to/cloudservice/venv/bin/gunicorn \
    --bind=127.0.0.1:8000 \
    --workers=4 \
    --worker-class=sync \
    --timeout=120 \
    config.wsgi:application
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/cloudservice.log

[program:celery]
directory=/path/to/cloudservice/cloudservice
command=/path/to/cloudservice/venv/bin/celery \
    -A config worker \
    --loglevel=info \
    --concurrency=4
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery.log

[program:celery-beat]
directory=/path/to/cloudservice/cloudservice
command=/path/to/cloudservice/venv/bin/celery \
    -A config beat \
    --loglevel=info
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery-beat.log
```

Update and restart supervisor:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

### 8. Backup Configuration

```bash
# Create backup script
sudo nano /usr/local/bin/backup-cloudservice.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backups/cloudservice"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="cloudservice"
DB_USER="cloudservice_user"

mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /path/to/cloudservice/media/

# Delete old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-cloudservice.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-cloudservice.sh
```

## 🐳 Docker Deployment

### Using Docker Compose on Production

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# View logs
docker-compose logs -f
```

## 🔍 Health Checks & Monitoring

### Application Health

```bash
# Check Django application
curl -I http://localhost:8000/health/

# Check API
curl -I http://localhost:8000/api/

# Check database
curl -I http://localhost:8000/admin/

# Check Redis
redis-cli ping
```

### Monitoring Setup

```bash
# Install Prometheus exporter
pip install django-prometheus

# Configure in settings.py
# Add to INSTALLED_APPS:
# 'django_prometheus'

# Update urls.py
# path('metrics/', include('django_prometheus.urls'))

# View metrics
curl http://localhost:8000/metrics/
```

## 📊 Performance Tuning

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_files_owner ON core_storagefile(owner_id);
CREATE INDEX idx_files_folder ON core_storagefile(folder_id);
CREATE INDEX idx_shares_user ON sharing_usershare(shared_with_id);

-- Vacuum database
VACUUM ANALYZE;
```

### Redis Optimization

```bash
# Monitor Redis memory
redis-cli INFO memory

# Set memory policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Persist to disk
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### Nginx Optimization

```nginx
# In nginx.conf
worker_processes auto;
worker_connections 2048;

# Enable gzip
gzip on;
gzip_comp_level 6;
gzip_types text/plain text/css application/json;

# Caching
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=http_cache:10m;
proxy_cache http_cache;
proxy_cache_valid 200 302 10m;
```

## 🔐 Security Hardening

### Firewall Configuration

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow only from specific IPs (optional)
sudo ufw allow from 10.0.0.0/8
```

### SSL/TLS Configuration

```bash
# Test SSL configuration
sudo ssl-test yourdomain.com

# Auto-renew certificates
sudo certbot renew --dry-run
sudo systemctl enable certbot.timer
```

### System Hardening

```bash
# Disable root login
sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

# Disable password authentication
sudo sed -i 's/^#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sudo sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

# Restart SSH
sudo systemctl restart ssh
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Multiple Gunicorn workers
gunicorn --workers 8 config.wsgi:application

# Load balancing with Nginx
upstream django {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}
```

### Vertical Scaling

```bash
# Increase server resources
# - CPU
# - RAM
# - Disk space

# Database connection pooling
# Use pgBouncer or similar
```

## 🐛 Troubleshooting

### Common Issues

```bash
# Check logs
tail -f /var/log/cloudservice.log
docker-compose logs -f web

# Database connection issues
sudo -u postgres psql -d cloudservice -c "SELECT 1"

# Redis connection issues
redis-cli PING

# Static files not loading
python manage.py collectstatic --clear

# Permission issues
sudo chown -R clouduser:clouduser /path/to/cloudservice
```

## 📞 Support & Maintenance

### Regular Maintenance

- [ ] Weekly: Review logs for errors
- [ ] Weekly: Update dependencies
- [ ] Monthly: Database maintenance
- [ ] Monthly: Security updates
- [ ] Quarterly: Performance review

### Backup Testing

- [ ] Test database restore monthly
- [ ] Test application restore monthly
- [ ] Document recovery procedures

---

For more help, see [README.md](README.md) and the official documentation.
