# Django Platform Auth

Unified authentication package for multi-app Django platforms with SSO support.

## Features

- **Custom User Model**: Extensible user model with role-based access control
- **JWT Authentication**: Token-based authentication across apps
- **Cross-App SSO**: Single sign-on with domain-wide cookies
- **Multiple Roles**: Support for admin, support staff, customers, and custom roles
- **Storage Quota**: Built-in support for storage management
- **Preferences**: User preferences (language, timezone, theme)
- **Activity Tracking**: Last login and last activity timestamps
- **Flexible Deployment**: Support for subdomain, path-based, and port-based routing

## Installation

```bash
pip install -e git+https://github.com/yourusername/django-platform-auth.git#egg=django-platform-auth
```

For local development:

```bash
pip install -e /path/to/django-platform-auth
```

## Quick Start

### 1. Add to INSTALLED_APPS

In your Django settings.py:

```python
INSTALLED_APPS = [
    'platform_auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.auth',  # Optional, only if you need admin
    'rest_framework',
    'rest_framework_simplejwt',
    # ... other apps
]

AUTH_USER_MODEL = 'platform_auth.User'
```

### 2. Configure JWT

```python
from datetime import timedelta
import os

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY', SECRET_KEY),
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JTI_CLAIM': 'jti',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_DB_COLUMN': 'jti',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
}
```

### 3. Add Middleware (Optional for cookie-based SSO)

```python
MIDDLEWARE = [
    # ... existing middleware
    'platform_auth.middleware.PlatformJWTMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # ... other middleware
]
```

### 4. Configure Database Routing (For shared auth database)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'app_db',
        # ... other settings
    },
    'platform_auth_db': {  # Shared auth database
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'platform_auth',
        # ... connection settings
    }
}

DATABASE_ROUTERS = ['platform_auth.routers.PlatformAuthRouter']
```

### 5. Include URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('auth/', include('platform_auth.urls')),
    # ... other urls
]
```

### 6. Run Migrations

```bash
python manage.py migrate
```

## User Model

The `User` model combines features from multiple use cases:

### Fields

- **Basic Information**
  - `username`: Unique username
  - `email`: Email address (used as USERNAME_FIELD)
  - `first_name`: User's first name
  - `last_name`: User's last name
  - `password`: Hashed password

- **Role System**
  - `role`: User role (admin, support_agent, customer, user, moderator)
  - `support_level`: Support agent level (1-4, optional)

- **Storage & Quota**
  - `storage_quota`: Storage quota in bytes (default: 5GB)

- **Profile Information**
  - `phone`: Phone number
  - `department`: Department name
  - `location`: User location
  - `avatar`: Profile picture
  - `bio`: User biography
  - `website`: Website URL

- **Address Information**
  - `street`: Street address
  - `postal_code`: Postal code
  - `city`: City name
  - `country`: Country name

- **Preferences**
  - `language`: Language code (de, en, fr)
  - `timezone`: Timezone (default: Europe/Berlin)
  - `theme`: Theme preference (light, dark, auto)

- **OAuth Integration**
  - `microsoft_id`: Microsoft/Office365 ID
  - `microsoft_token`: Microsoft OAuth token

- **Status & Activity**
  - `is_active`: Account active status
  - `is_staff`: Admin panel access
  - `email_verified`: Email verification status
  - `is_two_factor_enabled`: 2FA status
  - `force_password_change`: Force password reset on next login
  - `last_login`: Last login timestamp
  - `last_activity`: Last activity timestamp
  - `created_at`: Account creation timestamp
  - `updated_at`: Last modification timestamp

- **Extensibility**
  - `app_settings`: JSON field for app-specific settings

## Authentication

### JWT Token Endpoints

```
POST /auth/login/
POST /auth/token/refresh/
POST /auth/logout/
```

### Example Login

```bash
curl -X POST http://localhost:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "app_name": "cloude"
  }'
```

Response:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "john_doe",
    "role": "customer"
  }
}
```

## API Endpoints

- `GET /auth/user/profile/` - Get current user profile
- `PUT /auth/user/profile/` - Update user profile
- `POST /auth/user/change-password/` - Change password
- `POST /auth/user/logout/` - Logout (blacklist token)

## Configuration

### SSO Cookie Domain

For subdomain-based SSO:

```python
SSO_COOKIE_DOMAIN = '.yourdomain.com'
SSO_COOKIE_SECURE = True  # HTTPS only
SSO_COOKIE_SAMESITE = 'Lax'
```

### Custom User Model Fields

Extend the User model by creating proxy models or using composition:

```python
from platform_auth.models import User

class CustomUser(User):
    custom_field = models.CharField(max_length=100)

    class Meta:
        proxy = True
```

## Permissions

The User model includes Django's permission system:

```python
from django.contrib.auth.models import Permission

# Check permissions
if user.has_perm('myapp.view_items'):
    # User has permission
    pass

# Check role-based access
if user.role == 'admin':
    # User is admin
    pass
```

## Testing

```python
from django.test import TestCase
from platform_auth.models import User

class UserTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_user_creation(self):
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))
```

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please open an issue on GitHub:
https://github.com/yourusername/django-platform-auth/issues
