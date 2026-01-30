#!/usr/bin/env python
"""Setup root folders for all users"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import StorageFolder

print("[*] Setup Root-Folders fuer alle Benutzer...")
print()

for user in User.objects.all():
    # Skip AnonymousUser
    if not user.is_active:
        continue

    # Überprüfe, ob Root-Folder existiert
    root_folder = StorageFolder.objects.filter(
        owner=user,
        parent=None
    ).first()

    if root_folder:
        print("[OK] {}: Hat Root-Folder (ID: {})".format(user.username, root_folder.id))
    else:
        print("[..] {}: Erstelle Root-Folder...".format(user.username))
        # Erstelle Root-Folder
        root_folder = StorageFolder.objects.create(
            owner=user,
            parent=None,
            name='Root',
            description='Root folder'
        )
        print("[OK] Root-Folder erstellt (ID: {})".format(root_folder.id))

print()
print("[SUCCESS] Alle Benutzer haben Root-Folders!")
