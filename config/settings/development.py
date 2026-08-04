"""Local development settings: SQLite by default, permissive CORS, verbose logging."""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']

SECRET_KEY = SECRET_KEY or 'django-insecure-qhwmr8rbcjpro+)8ci_9_deimibba)r0%zw@=oxi-)$v#wsbjf'

CORS_ALLOW_ALL_ORIGINS = True

LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['inventory']['level'] = 'DEBUG'
