#!/bin/bash
#
# Django Platform - Docker-Compose Installation Script
# Quick setup for Linux and macOS
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
clear
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║    Django Platform - Docker Installation              ║"
echo "║    Cloude (Cloud Storage) + HelpDesk (Ticketing)     ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}[1/5] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker first.${NC}"
    echo "  Visit: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found. Please install Docker Compose.${NC}"
    echo "  Visit: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Get configuration from user
echo -e "\n${YELLOW}[2/5] Configuration${NC}"

read -p "Enter domain (e.g., yourdomain.com) [localhost]: " DOMAIN
DOMAIN=${DOMAIN:-localhost}
echo "Domain: ${DOMAIN}"

read -p "Install Cloude (Cloud Storage)? (y/n) [y]: " INSTALL_CLOUDE
INSTALL_CLOUDE=${INSTALL_CLOUDE:-y}

read -p "Install HelpDesk (Support Ticketing)? (y/n) [y]: " INSTALL_HELPDESK
INSTALL_HELPDESK=${INSTALL_HELPDESK:-y}

if [ "$INSTALL_CLOUDE" != "y" ] && [ "$INSTALL_HELPDESK" != "y" ]; then
    echo -e "${RED}✗ You must install at least one application.${NC}"
    exit 1
fi

# Generate secure passwords
echo -e "\n${YELLOW}[3/5] Generating secure passwords...${NC}"

DB_ROOT_PASSWORD=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 64)
CLOUDE_SECRET=$(openssl rand -base64 50)
HELPDESK_SECRET=$(openssl rand -base64 50)

echo -e "${GREEN}✓ Passwords generated${NC}"

# Create .env file
echo -e "${YELLOW}[4/5] Creating .env configuration...${NC}"

cat > .env <<EOF
# Auto-generated configuration
DB_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
DB_USER=platform_user
DB_PASSWORD=${DB_PASSWORD}

JWT_SECRET_KEY=${JWT_SECRET}
SSO_COOKIE_DOMAIN=.${DOMAIN}

CLOUDE_DEBUG=False
CLOUDE_SECRET_KEY=${CLOUDE_SECRET}
CLOUDE_ALLOWED_HOSTS=cloude.${DOMAIN},${DOMAIN}

HELPDESK_DEBUG=False
HELPDESK_SECRET_KEY=${HELPDESK_SECRET}
HELPDESK_ALLOWED_HOSTS=helpdesk.${DOMAIN},support.${DOMAIN},${DOMAIN}

EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
LANGUAGE_CODE=de-de
TIME_ZONE=Europe/Berlin
EOF

echo -e "${GREEN}✓ .env file created${NC}"

# Start Docker services
echo -e "\n${YELLOW}[5/5] Starting Docker services...${NC}"
echo "This may take a few minutes on first run..."

docker-compose pull
docker-compose build

# Start services
docker-compose up -d

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 15

# Run migrations
if [ "$INSTALL_CLOUDE" = "y" ]; then
    echo -e "\n${BLUE}Running Cloude migrations...${NC}"
    docker-compose exec -T cloude_web python manage.py migrate || true
    docker-compose exec -T cloude_web python manage.py collectstatic --noinput || true
fi

if [ "$INSTALL_HELPDESK" = "y" ]; then
    echo -e "\n${BLUE}Running HelpDesk migrations...${NC}"
    docker-compose exec -T helpdesk_web python manage.py migrate || true
    docker-compose exec -T helpdesk_web python manage.py collectstatic --noinput || true
fi

# Print access information
echo -e "\n${GREEN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║         Installation Complete!                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

if [ "$INSTALL_CLOUDE" = "y" ]; then
    echo -e "${BLUE}Cloude (Cloud Storage):${NC}"
    echo "  Web:       http://cloude.${DOMAIN}"
    echo "  Admin:     http://cloude.${DOMAIN}/admin"
fi

if [ "$INSTALL_HELPDESK" = "y" ]; then
    echo -e "${BLUE}HelpDesk (Support Ticketing):${NC}"
    echo "  Web:       http://helpdesk.${DOMAIN}"
    echo "  Admin:     http://helpdesk.${DOMAIN}/admin"
fi

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Edit /etc/hosts or configure your domain DNS"
echo "   For localhost testing, add to /etc/hosts:"
echo "   127.0.0.1 cloude.${DOMAIN} helpdesk.${DOMAIN}"
echo ""
echo "2. Create superuser accounts:"
if [ "$INSTALL_CLOUDE" = "y" ]; then
    echo "   docker-compose exec cloude_web python manage.py createsuperuser"
fi
if [ "$INSTALL_HELPDESK" = "y" ]; then
    echo "   docker-compose exec helpdesk_web python manage.py createsuperuser"
fi
echo ""
echo "3. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "4. Stop services:"
echo "   docker-compose down"
echo ""

# Save credentials to file
echo -e "${YELLOW}Credentials saved to: .env${NC}"
echo "Keep this file safe - it contains database passwords!"
echo ""

echo -e "${GREEN}✓ Installation finished!${NC}"
