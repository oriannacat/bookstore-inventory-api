"""Production settings: enforces a managed Postgres DB, a real SECRET_KEY, and an
explicit ALLOWED_HOSTS/CORS allowlist. Fails fast at boot if misconfigured instead
of silently falling back to insecure defaults."""

import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY debe estar definida en producción.')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS debe estar definida en producción.')

# The business rule requires a managed database in production — no SQLite fallback.
if not DATABASE_URL:
    raise ImproperlyConfigured(
        'DATABASE_URL debe estar definida en producción (no se permite SQLite).'
    )
# Managed providers (Render, etc.) require SSL; a local docker-compose Postgres
# container does not, so this can be disabled with DB_SSL_REQUIRE=False.
DB_SSL_REQUIRE = os.getenv('DB_SSL_REQUIRE', 'True') == 'True'
DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=DB_SSL_REQUIRE)
}

CORS_ALLOW_ALL_ORIGINS = False

# Disabled by default for a plain-HTTP local docker-compose run; managed cloud
# deployments (Render, etc.) sit behind an HTTPS-terminating proxy and should
# leave this at its default (True).
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
