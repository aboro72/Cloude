#!/usr/bin/env python
"""Quick login test script"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

# Create a test client
client = Client()

# Verify admin user exists
try:
    admin = User.objects.get(username='admin')
    print(f"[+] Admin user found: {admin.username}")
    print(f"[+] Admin is_active: {admin.is_active}")
except User.DoesNotExist:
    print("[ERROR] Admin user not found!")
    exit(1)

# Test POST login
print("\n[*] Testing login with POST request...")
response = client.post('/accounts/login/', {
    'username': 'admin',
    'password': 'admin'
})

print(f"[+] Response status code: {response.status_code}")

if response.status_code == 302:
    print(f"[+] Redirect location: {response.get('Location', 'N/A')}")
    print("[SUCCESS] Login returned 302 redirect!")
elif response.status_code == 200:
    print("[!] Login returned 200 - form still displayed or error")
    content = response.content.decode('utf-8', errors='ignore')

    if 'Invalid' in content or 'incorrect' in content.lower():
        print("[ERROR] Login credentials were invalid")
        print(content[content.find('Invalid'):content.find('Invalid')+200])
    elif 'non_field_errors' in content:
        print("[ERROR] Non-field form errors detected")
    else:
        print("[INFO] Form may have other validation issues")
else:
    print(f"[ERROR] Unexpected status code: {response.status_code}")

print("\n[*] Testing login with follow=True...")
response = client.post('/accounts/login/', {
    'username': 'admin',
    'password': 'admin'
}, follow=True)

print(f"[+] Final status code: {response.status_code}")
if hasattr(response, 'request'):
    print(f"[+] Final URL: {response.request.get('PATH_INFO', 'N/A')}")

    if '/core/' in response.request.get('PATH_INFO', ''):
        print("[SUCCESS] Login successful and redirected to dashboard!")
    else:
        print(f"[!] Login redirected to: {response.request.get('PATH_INFO', 'unknown')}")
