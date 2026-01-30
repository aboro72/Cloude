#!/usr/bin/env python
"""
HTTP-basierter Login-Test
Simuliert einen Browser-Login ohne Django's Test-Framework
"""
import requests
import sys
import time
from urllib.parse import urljoin

# Konfiguration
BASE_URL = 'http://localhost:8000'
LOGIN_URL = urljoin(BASE_URL, '/accounts/login/')
CREDENTIALS = {
    'username': 'admin',
    'password': 'admin'
}

print("[*] Login-Test via HTTP")
print(f"[*] Zielserver: {BASE_URL}")
print(f"[*] Login-URL: {LOGIN_URL}")
print()

# Session erstellen (für Cookie-Handling)
session = requests.Session()

# Schritt 1: Login-Seite abrufen (GET)
print("[*] Schritt 1: Login-Seite abrufen...")
try:
    response = session.get(LOGIN_URL, timeout=10)
    print(f"[+] Status: {response.status_code}")

    if response.status_code == 200:
        print("[+] Login-Seite erfolgreich abgerufen")

        # CSRF-Token extrahieren
        if 'csrfmiddlewaretoken' in response.text:
            import re
            csrf_match = re.search(r'csrfmiddlewaretoken["\']?\s*value=["\']([^"\']+)["\']', response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                print(f"[+] CSRF-Token gefunden: {csrf_token[:20]}...")
            else:
                print("[!] CSRF-Token nicht extrahierbar")
                csrf_token = None
        else:
            print("[!] CSRF-Token nicht gefunden")
            csrf_token = None
    else:
        print(f"[ERROR] Unerwarteter Status: {response.status_code}")
        sys.exit(1)
except requests.exceptions.Timeout:
    print("[ERROR] Timeout beim Abrufen der Login-Seite")
    sys.exit(1)
except requests.exceptions.ConnectionError as e:
    print(f"[ERROR] Verbindungsfehler: {e}")
    print("[*] Stelle sicher, dass der Server läuft:")
    print("    python manage.py runserver")
    sys.exit(1)

print()

# Schritt 2: Login-Formular absenden (POST)
print("[*] Schritt 2: Login-Formular absenden...")
login_data = {
    'username': CREDENTIALS['username'],
    'password': CREDENTIALS['password'],
}

if csrf_token:
    login_data['csrfmiddlewaretoken'] = csrf_token

try:
    print(f"[*] Sende POST-Anfrage mit Daten: {{'username': '{login_data['username']}', 'password': '***'}}")

    start_time = time.time()
    response = session.post(LOGIN_URL, data=login_data, timeout=15, allow_redirects=False)
    elapsed = time.time() - start_time

    print(f"[+] Antwortzeit: {elapsed:.2f} Sekunden")
    print(f"[+] Status: {response.status_code}")

    if response.status_code == 302:
        redirect_url = response.headers.get('Location', 'N/A')
        print(f"[SUCCESS] Login erfolgreich!")
        print(f"[+] Redirect zu: {redirect_url}")

        # Folge dem Redirect
        print()
        print("[*] Schritt 3: Folge dem Redirect...")
        try:
            redirect_response = session.get(urljoin(BASE_URL, redirect_url), timeout=10)
            print(f"[+] Redirect-Status: {redirect_response.status_code}")

            if redirect_response.status_code == 200:
                if 'dashboard' in redirect_response.text.lower() or 'willkommen' in redirect_response.text.lower():
                    print("[SUCCESS] Dashboard erfolgreich geladen!")
                else:
                    print("[!] Dashboard-Seite geladen, aber Inhalt unbekannt")
            else:
                print(f"[ERROR] Fehler beim Laden des Dashboards: {redirect_response.status_code}")
        except Exception as e:
            print(f"[ERROR] Fehler beim Redirect: {e}")

    elif response.status_code == 200:
        print("[!] Login returned 200 - Form wurde erneut angezeigt (Login fehlgeschlagen)")

        # Überprüfe auf Fehlermeldungen
        if 'Invalid' in response.text or 'incorrect' in response.text.lower():
            print("[ERROR] Ungültige Anmeldedaten!")
        elif 'CSRF' in response.text:
            print("[ERROR] CSRF-Validierungsfehler!")
        else:
            print("[!] Unbekannter Fehler - bitte Server-Logs überprüfen")
    else:
        print(f"[ERROR] Unerwarteter Status: {response.status_code}")

except requests.exceptions.Timeout:
    print("[ERROR] Timeout beim Login")
    print("[*] Der Server antwortet nicht schnell genug")
    print("[*] Überprüfe Server-Logs auf Fehler")
except Exception as e:
    print(f"[ERROR] Fehler: {e}")

print()
print("[*] Test abgeschlossen")
print()
print("[*] Tipps:")
print("  - Überprüfe Server-Logs: 'python manage.py runserver'")
print("  - Überprüfe Datenbankverbindung: 'python manage.py check'")
print("  - Überprüfe Benutzer: 'python manage.py create_demo_users'")
