# HelpDesk Migration Guide: accounts.User → platform_auth.User

## Overview

This guide walks you through migrating HelpDesk from its custom `accounts.User` model to the unified `platform_auth.User` model.

**Timeline:** ~30-60 minutes (with backup creation)
**Risk Level:** Medium (data preservation critical)
**Rollback:** Possible with database backup

## Prerequisites

1. **Database Backup**
   ```bash
   # MySQL backup
   mysqldump -u your_user -p helpdesk_db > helpdesk_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Platform Auth Package**
   ```bash
   pip install -e C:\Users\aborowczak\PycharmProjects\django-platform-auth
   ```

3. **Requirements Update**
   Add to HelpDesk `requirements.txt`:
   ```
   django-platform-auth>=0.1.0
   mysqlclient>=2.2.0
   ```

## Step-by-Step Migration

### Step 1: Update requirements.txt

```bash
cd C:\Users\aborowczak\PycharmProjects\HelpDesk
pip install -e C:\Users\aborowczak\PycharmProjects\django-platform-auth
pip install mysqlclient
```

### Step 2: Update settings.py

**File:** `helpdesk/settings.py`

**Change 1 - Add platform_auth to INSTALLED_APPS (line ~47):**
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Platform Authentication (add this - MUST be before apps.accounts)
    'platform_auth',

    # ... rest of third-party apps

    # Local apps (keep apps.accounts for other models)
    'apps.accounts',
    'apps.tickets',
    'apps.knowledge',
    'apps.chat',
    'apps.admin_panel',
    'apps.main',
]
```

**Change 2 - Update AUTH_USER_MODEL (line 167):**
```python
# OLD:
# AUTH_USER_MODEL = 'accounts.User'

# NEW:
AUTH_USER_MODEL = 'platform_auth.User'
```

**Change 3 - Add JWT Configuration (after line 186):**
```python
# JWT/SSO Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY', SECRET_KEY),
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# SSO Cookie Configuration
SSO_COOKIE_NAME = 'platform_sso_token'
SSO_COOKIE_DOMAIN = os.getenv('SSO_COOKIE_DOMAIN', None)
SSO_COOKIE_SECURE = not DEBUG
SSO_COOKIE_SAMESITE = 'Lax'

# Add platform_auth to REST_FRAMEWORK authentication
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'platform_auth.backends.PlatformJWTAuthentication',  # Add this
    'rest_framework.authentication.SessionAuthentication',
    'rest_framework.authentication.TokenAuthentication',
]
```

**Change 4 - Add Middleware (after line 85):**
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.chat.middleware.ChatCorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'platform_auth.middleware.ActivityTrackingMiddleware',  # Add this
    'apps.accounts.activity_middleware.ActivityTrackingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.chat.middleware.ChatWidgetFrameMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.accounts.middleware.ForcePasswordChangeMiddleware',
]
```

### Step 3: Create Initial Migration

Run platform_auth initial migration:

```bash
python manage.py migrate platform_auth
```

This creates the `platform_users` table with all fields.

### Step 4: Create Data Migration

Create a new data migration to copy existing users:

```bash
python manage.py makemigrations accounts --empty --name migrate_to_platform_auth
```

This creates a file like `apps/accounts/migrations/0007_migrate_to_platform_auth.py`

**Edit this file** and replace the empty `operations` list with:

```python
from django.db import migrations
from django.contrib.auth import get_user_model as get_platform_user


def migrate_users(apps, schema_editor):
    """Copy users from accounts.User to platform_auth.User"""
    OldUser = apps.get_model('accounts', 'User')
    NewUser = apps.get_model('platform_auth', 'User')

    # Get all old users
    old_users = OldUser.objects.all()

    print(f"\n🔄 Migrating {old_users.count()} users...")

    migrated_count = 0
    error_count = 0

    for old_user in old_users:
        try:
            # Check if user already exists in new table
            if NewUser.objects.filter(id=old_user.id).exists():
                print(f"⚠️  User {old_user.email} already exists, skipping...")
                continue

            # Create new user with exact same data
            new_user = NewUser.objects.create(
                id=old_user.id,
                username=old_user.username,
                email=old_user.email,
                first_name=old_user.first_name,
                last_name=old_user.last_name,
                password=old_user.password,  # Password hash is portable
                is_active=old_user.is_active,
                is_staff=old_user.is_staff,
                is_superuser=old_user.is_superuser,
                last_login=old_user.last_login,
                created_at=old_user.created_at,
                updated_at=old_user.updated_at,
                # HelpDesk-specific fields
                role=old_user.role,
                support_level=old_user.support_level,
                phone=old_user.phone,
                department=old_user.department,
                location=old_user.location,
                email_verified=old_user.email_verified,
                is_two_factor_enabled=False,  # Not migrating 2FA settings
                force_password_change=old_user.force_password_change,
                last_activity=old_user.last_activity,
                street=old_user.street,
                postal_code=old_user.postal_code,
                city=old_user.city,
                country=old_user.country,
            )

            # Copy groups and permissions
            new_user.groups.set(old_user.groups.all())
            new_user.user_permissions.set(old_user.user_permissions.all())

            migrated_count += 1
            print(f"✓ Migrated: {old_user.email}")

        except Exception as e:
            error_count += 1
            print(f"✗ Error migrating {old_user.email}: {str(e)}")

    print(f"\n✅ Migration complete: {migrated_count} users migrated, {error_count} errors")


def rollback_migration(apps, schema_editor):
    """Rollback: delete migrated users from platform_auth"""
    NewUser = apps.get_model('platform_auth', 'User')
    NewUser.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_user_last_activity'),
        ('platform_auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_users, rollback_migration),
    ]
```

### Step 5: Run Migration

```bash
python manage.py migrate accounts
```

Verify no errors occurred. You should see output like:
```
✅ Migration complete: 25 users migrated, 0 errors
Running migrations:
  Applying accounts.0007_migrate_to_platform_auth... OK
```

### Step 6: Verify Data Integrity

```bash
python manage.py shell
```

Then in the Python shell:

```python
from django.contrib.auth import get_user_model

User = get_user_model()

# Check total users
print(f"Total users: {User.objects.count()}")

# Check admin users exist
print(f"Admin users: {User.objects.filter(role='admin').count()}")

# Check a specific user
admin_user = User.objects.filter(role='admin').first()
print(f"Admin user: {admin_user.email}")
print(f"Can login: {admin_user.check_password('your_password')}")

# Check groups were migrated
print(f"Users with groups: {User.objects.filter(groups__isnull=False).distinct().count()}")
```

### Step 7: Update ForeignKey References

Since HelpDesk already uses `settings.AUTH_USER_MODEL`, most references should work automatically. However, verify:

```bash
# Search for direct 'accounts.User' references
grep -r "'accounts\.User'" C:\Users\aborowczak\PycharmProjects\HelpDesk\apps --include="*.py"
```

If found, replace with `settings.AUTH_USER_MODEL` or the app model reference.

### Step 8: Run Tests

```bash
# Run user-related tests
python manage.py test apps.accounts

# Run all tests
python manage.py test
```

### Step 9: Test Login

1. Start server:
   ```bash
   python manage.py runserver
   ```

2. Visit http://localhost:8000/auth/login/

3. Try logging in with an existing user account

4. Verify you can access your dashboard

### Step 10: Clean Up (Optional)

Once migration is verified successful and you've confirmed no issues:

```bash
# You can optionally keep or delete the old accounts.User model
# For now, it's safer to keep it for reference
```

## Troubleshooting

### Error: "Duplicate entry for key 'email'"

**Cause:** User already exists in platform_auth table
**Solution:** Modify migration to skip existing users (code above already does this)

### Error: "Foreign key constraint fails"

**Cause:** Tickets reference users that weren't migrated
**Solution:** Ensure all users are migrated before running migration

### Users can't login after migration

**Cause:** Password hashes weren't copied correctly
**Solution:**
```python
# In Django shell, verify password works:
user = User.objects.get(email='your@email.com')
user.check_password('your_password')  # Should return True
```

## Rollback Procedure

If something goes wrong:

```bash
# Restore database from backup
mysql -u your_user -p helpdesk_db < helpdesk_backup_YYYYMMDD_HHMMSS.sql

# Revert settings.py changes
# Set AUTH_USER_MODEL back to 'accounts.User'
# Remove platform_auth from INSTALLED_APPS

# Delete the migration file you created
rm apps/accounts/migrations/0007_migrate_to_platform_auth.py

# Continue with old system
```

## Verification Checklist

After migration:

- [ ] All users can login
- [ ] User count matches pre-migration
- [ ] Password login works
- [ ] Role-based permissions work
- [ ] All tickets still have correct ownership
- [ ] Admin panel works
- [ ] Email configurations still work
- [ ] Celery tasks still work (if configured)

## Next Steps

After successful migration of HelpDesk:

1. Follow the same process for **Cloude**
2. Set up **Docker-Compose** with shared MariaDB
3. Configure **SSO** between both applications
4. Create **Installation scripts** for deployment

---

**Questions?** Check the Plan file or refer to platform_auth documentation.
