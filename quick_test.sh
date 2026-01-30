#!/bin/bash
# Quick-Test Script für Login-Funktionalität

echo "==================================="
echo "CloudService - Quick Test Script"
echo "==================================="
echo ""

cd cloudservice

# Test 1: Django System-Checks
echo "[1/5] Überprüfe Django System..."
python manage.py check
if [ $? -eq 0 ]; then
    echo "[✓] Django OK"
else
    echo "[✗] Django ERROR"
    exit 1
fi
echo ""

# Test 2: Überprüfe Benutzer
echo "[2/5] Überprüfe Benutzer..."
python manage.py shell << EOF
from django.contrib.auth.models import User
try:
    admin = User.objects.get(username='admin')
    print(f"[✓] Admin-Benutzer existiert: {admin.username}")
except:
    print("[✗] Admin-Benutzer nicht gefunden")
    print("[*] Führe create_demo_users aus...")
EOF
echo ""

# Test 3: Teste Authentifizierung
echo "[3/5] Teste Authentifizierung..."
python manage.py shell << EOF
from django.contrib.auth import authenticate
user = authenticate(username='admin', password='admin')
if user:
    print(f"[✓] Authentifizierung OK: {user.username}")
else:
    print("[✗] Authentifizierung FAILED")
EOF
echo ""

# Test 4: Überprüfe Settings
echo "[4/5] Überprüfe Settings..."
python manage.py shell << EOF
from django.conf import settings
print(f"[✓] DEBUG: {settings.DEBUG}")
print(f"[✓] ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"[✓] LOGIN_URL: {settings.LOGIN_URL if hasattr(settings, 'LOGIN_URL') else 'Not set'}")
EOF
echo ""

# Test 5: Zeige wichtige URLs
echo "[5/5] Wichtige URLs:"
echo "  Login:    http://localhost:8000/accounts/login/"
echo "  Dashboard: http://localhost:8000/core/"
echo "  Admin:    http://localhost:8000/admin/"
echo "  API:      http://localhost:8000/api/docs/"
echo ""

echo "==================================="
echo "Server starten mit:"
echo "  python manage.py runserver"
echo "==================================="
