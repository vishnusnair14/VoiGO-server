"""
Django settings for VoiGO project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import logging.config
import os
from pathlib import Path

from django.conf import settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-%#tpiy69cdle!8ip83bz%0$s13eis1rli3h(qe_n8&-1m&0*0-'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'big-terminally-lacewing.ngrok-free.app'
]

# Application definition
INSTALLED_APPS = [
    'channels',
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'server',
    'rest_framework',
    'huey.contrib.djhuey',
    'bx_django_utils',
    'huey_monitor',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'VoiGO.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'VoiGO.wsgi.application'

ASGI_APPLICATION = 'VoiGO.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Default email SMTP backend configs
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587  # Gmail SMTP port
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'voigo.delivery@gmail.com'  # TODO
EMAIL_HOST_PASSWORD = os.environ.get('USER_PASSWORD')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#
# # Add these configurations
# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Settings for huey
HUEY = {
    'huey_class': 'huey.SqliteHuey',
    "name": 'sqla+sqlite:///db.huey.sqlite3',
    "immediate": False,
    "results": True,
    'consumer': {
        'workers': 1,
        'worker_type': 'thread',
        'initial_delay': 0.1,  # Smallest polling interval, same as -d
        'backoff': 1.15,  # Exponential backoff using this rate, -b
        'max_delay': 1.0,  # Max possible polling interval, -m
        'scheduler_interval': 1,  # Check schedule every second, -s
        'periodic': True,  # Enable crontab feature
        'check_worker_health': True,  # Enable worker health checks
        'health_check_interval': 120,  # Check worker health every second
    }
}

# Settings for logging
# Define custom logging levels
SUCCESS_LEVEL = 23
INFO_DATA_LEVEL = 25

logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")
logging.addLevelName(INFO_DATA_LEVEL, "DATA")


def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)


def info_data(self, message, *args, **kwargs):
    if self.isEnabledFor(INFO_DATA_LEVEL):
        self._log(INFO_DATA_LEVEL, message, args, **kwargs)


logging.Logger.success = success
logging.Logger.info_data = info_data

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s%(levelname)s: %(message)s',
            'log_colors': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'SUCCESS': 'bold_green',
                'DATA': 'blue',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        },
        'file': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'debug.log'),
            'formatter': 'file',
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

logging.config.dictConfig(settings.LOGGING)
log = logging.getLogger(__name__)
