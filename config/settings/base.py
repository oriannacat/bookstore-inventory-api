"""Shared settings. Never imported directly — use `development` or `production`."""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = False
ALLOWED_HOSTS = []


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'drf_spectacular',
    'corsheaders',
    'inventory',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# Uses DATABASE_URL when present (Docker / cloud deployment with managed Postgres),
# falls back to local SQLite for a zero-config quickstart in development.
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'EXCEPTION_HANDLER': 'inventory.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # This API doesn't use Django login (Session/Basic auth) at all — access is
    # governed entirely by HasAPIKeyForWrite (see inventory/permissions.py).
    # Leaving DRF's Session/Basic authenticators enabled by default made Swagger
    # show a misleading lock on every endpoint, and any *invalid* credentials
    # sent via its "Authorize" dialog would reject even public GET requests
    # before the permission check ever ran.
    'DEFAULT_AUTHENTICATION_CLASSES': [],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Bookstore Inventory API',
    'DESCRIPTION': (
        'API REST para gestion de inventario de librerias, con validacion de '
        'precios en tiempo real contra tasas de cambio.\n\n'
        'Autenticacion: la lectura (GET) es siempre publica. Si el despliegue '
        'configura la variable de entorno API_KEY, las operaciones de escritura '
        '(POST/PUT/PATCH/DELETE) requieren el header "X-API-Key". Si no esta '
        'configurada, la escritura tambien es publica.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}


# CORS - locked down by default, opened explicitly in development.py
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]


# Business configuration for the exchange-rate/price-calculation feature

EXCHANGE_RATE_API_URL = os.getenv(
    'EXCHANGE_RATE_API_URL', 'https://api.exchangerate-api.com/v4/latest/USD'
)
LOCAL_CURRENCY = os.getenv('LOCAL_CURRENCY', 'EUR')
DEFAULT_EXCHANGE_RATE = float(os.getenv('DEFAULT_EXCHANGE_RATE', '0.85'))
PROFIT_MARGIN_PERCENTAGE = float(os.getenv('PROFIT_MARGIN_PERCENTAGE', '40'))
EXCHANGE_RATE_CACHE_TTL_SECONDS = int(os.getenv('EXCHANGE_RATE_CACHE_TTL_SECONDS', '300'))

# Opt-in API key for write operations (POST/PUT/PATCH/DELETE on /books/).
# Leave unset to keep the API fully open (e.g. while it's being evaluated).
API_KEY = os.getenv('API_KEY', '')


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'inventory': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
