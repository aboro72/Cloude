"""
Django settings for CloudService project.
Django 5.x Configuration
"""
import os
import sys
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CLOUDSERVICE_DIR = Path(__file__).resolve().parent.parent

# Make plugins/installed importable (needed for URL includes at startup)
_plugins_dir = str(BASE_DIR / 'plugins' / 'installed')
if _plugins_dir not in sys.path:
    sys.path.insert(0, _plugins_dir)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-your-secret-key-change-in-production'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# Allow all hosts in development, restrict in production
if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
DJANGO_APPS = [
    'daphne',  # WebSocket support for Django 5.x
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_filters',
    'django_extensions',
    'crispy_forms',
    'crispy_bootstrap5',
    'guardian',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    'channels',
    'modeltranslation',
    'structlog',
    'jazzmin',  # Enhanced admin interface
]

LOCAL_APPS = [
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'storage.apps.StorageConfig',
    'sharing.apps.SharingConfig',
    'api.apps.ApiConfig',
    'plugins.apps.PluginsConfig',  # Plugin system for extensibility
    'news.apps.NewsConfig',
    'landing_editor.apps.LandingEditorConfig',
    'tasks_board.apps.TasksBoardConfig',
    'forms_builder.apps.FormsBuilderConfig',
    'departments.apps.DepartmentsConfig',
    'messenger.apps.MessengerConfig',
    'jitsi.apps.JitsiConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'django.contrib.sessions.middleware.SessionMiddleware',  # Sessions must come before CSRF
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'structlog.contextvars.clear_contextvars',  # Optional: uncomment if using structlog
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(CLOUDSERVICE_DIR, 'templates'),
        ],
        # APP_DIRS must be False when using custom loaders
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'core.context_processors.plugin_menu_items',
              ],
            # Custom loaders - PluginTemplateLoader dynamically finds plugin templates
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'plugins.template_loader.PluginTemplateLoader',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DB_ENGINE = config('DB_ENGINE', default='sqlite')

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': config('SQLITE_PATH', default=os.path.join(BASE_DIR, 'db.sqlite3')),
        }
    }
elif DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='cloudservice'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='3306'),
            'ATOMIC_REQUESTS': True,
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
                'charset': 'utf8mb4',
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='cloudservice'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='password'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'ATOMIC_REQUESTS': True,
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }

# Authentication Backends
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # Default
    'guardian.backends.ObjectPermissionBackend',  # Object-level permissions
)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'de-de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True
LANGUAGES = [
    ('de', 'Deutsch'),
    ('en', 'English'),
    ('fr', 'Français'),
]
LOCALE_PATHS = [
    os.path.join(CLOUDSERVICE_DIR, 'locale'),
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(CLOUDSERVICE_DIR, 'static'),
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Collabora / WOPI integration
COLLABORA_BASE_URL = config('COLLABORA_BASE_URL', default='https://office.aborosoft.com')
CLOUDSERVICE_EXTERNAL_URL = config('CLOUDSERVICE_EXTERNAL_URL', default='https://storage1.aborosoft.com')
COLLABORA_ACCESS_TOKEN_TTL = config('COLLABORA_ACCESS_TOKEN_TTL', default=3600, cast=int)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========== MongoDB Configuration (optional) ==========
# Wenn MONGODB_ENABLED=False oder keine Verbindung möglich → stiller Fallback,
# die App läuft normal mit SQLite/PostgreSQL weiter.
MONGODB_ENABLED = config('MONGODB_ENABLED', default=False, cast=bool)
MONGODB_HOST = config('MONGODB_HOST', default='localhost')
MONGODB_PORT = config('MONGODB_PORT', default=27017, cast=int)
MONGODB_DB = config('MONGODB_DB', default='appdb')
MONGODB_USER = config('MONGODB_USER', default='')
MONGODB_PASSWORD = config('MONGODB_PASSWORD', default='')
MONGODB_AUTH_SOURCE = config('MONGODB_AUTH_SOURCE', default='appdb')
MONGODB_CONNECT_TIMEOUT_MS = config('MONGODB_CONNECT_TIMEOUT_MS', default=3000, cast=int)
MONGODB_SERVER_SELECTION_TIMEOUT_MS = config('MONGODB_SERVER_SELECTION_TIMEOUT_MS', default=3000, cast=int)

# ========== REST Framework Configuration ==========
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
}

# ========== JWT Configuration ==========
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ========== CORS Configuration ==========
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True

# ========== Crispy Forms ==========
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ========== Redis Cache Configuration ==========
# Use in-memory cache in development, Redis in production
if DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    # Use database for sessions in development (reliable)
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
else:
    # Production: Use Redis
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/0'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                'IGNORE_EXCEPTIONS': True,
            }
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# ========== Celery Configuration ==========
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/1')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/2')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ========== Channels (WebSocket) Configuration ==========
ASGI_APPLICATION = 'config.asgi.application'

if DEBUG:
    # In-memory channel layer for development — no Redis required
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [config('REDIS_URL', default='redis://127.0.0.1:6379/0')],
                'capacity': 1500,
                'expiry': 10,
            },
        },
    }

# ========== File Upload Configuration ==========
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760   # 10 MB – darüber schreibt Django auf Disk statt RAM
DATA_UPLOAD_MAX_MEMORY_SIZE = None       # Kein Limit für Upload-Daten
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS = {
    # Documents
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'txt', 'csv', 'json', 'xml',
    # Images
    'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp',
    # Video
    'mp4', 'avi', 'mov', 'mkv', 'webm',
    # Audio
    'mp3', 'wav', 'flac', 'aac', 'ogg',
    # Archives
    'zip', 'rar', '7z', 'tar', 'gz',
    # Code
    'py', 'js', 'html', 'css', 'java', 'cpp', 'c', 'go', 'rs',
}

# ========== Security Settings ==========
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
# Honor reverse-proxy headers (nginx/Cloudflare) so Django can detect HTTPS correctly.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
    'https://storage1.aborosoft.com',
    'https://cloudshare.aborosoft.com',
]
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    'DEFAULT_SRC': ("'self'",),
    'SCRIPT_SRC': ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net"),
    'STYLE_SRC': ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net"),
    'IMG_SRC': ("'self'", "data:", "https:"),
    'FONT_SRC': ("'self'", "cdn.jsdelivr.net"),
}
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ========== Logging Configuration ==========
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'cloudservice.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'sentry_sdk.integrations.logging.EventHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'cloudservice': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# ========== Sentry Configuration (Optional) ==========
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production' if not DEBUG else 'development',
    )

# ========== Model Translation (i18n) ==========
MODELTRANSLATION_DEFAULT_LANGUAGE = 'de'
MODELTRANSLATION_FALLBACK_LANGUAGES = {
    'default': ('de', 'en'),
    'de': ('de', 'en'),
    'en': ('en', 'de'),
}

# ========== Django Admin Customization ==========
JAZZMIN = {
    "site_title": "CloudService Admin",
    "site_header": "CloudService",
    "site_logo": "/static/images/logo.png",
    "welcome_sign": "Willkommen zu CloudService",
    "copyright": "CloudService Team",
    "search_model": ["auth.User", "storage.StorageFile"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.add_user"]},
        {"app": "storage"},
    ],
    "usermenu_links": [
        {"model": "auth.user"}
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_models": [],
    "default_icon_parents": "fas fa-chevron-right",
    "default_icon_children": "fas fa-arrow-right",
}

# Jitsi Meet Integration
JITSI_APP_ID = config("JITSI_APP_ID", default="cloudshare")
JITSI_APP_SECRET = config("JITSI_APP_SECRET", default="")
JITSI_URL = config("JITSI_URL", default="https://meet.aborosoft.com")
