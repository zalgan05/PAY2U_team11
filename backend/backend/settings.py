# flake8: noqa
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-4a3#b1o&qv_4v*2dlz%78jvig@l3wv&s!0z@dg*7upit8%zsqv'

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Значение True запустит на SQLite, иначе - Postgres
USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true'

# Версия АПИ
VERSION_API = os.getenv('VERSION_API', '1')

# Если TEST_CELERY установлено в True, используем задержку в 10 секунд для отладки.
# В противном случае используем запланированное время выполнения для даты следующего списания.
TEST_CELERY = os.getenv('DEBUG', 'False').lower() == 'true'

DEFAULT_REDIS_HOST = os.getenv('DEFAULT_REDIS_HOST', 'redis')

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '93.183.93.2', 'pay2uteam11.ddns.net']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    'django_filters',
    'celery',
    'corsheaders',

    'users',
    'subscriptions',
    'api'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

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

WSGI_APPLICATION = 'backend.wsgi.application'


if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'postgres'),
            'USER': os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', 5432)
        }
    }


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


LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'collected_static'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Spectacular settings (API documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Список эндпоинтов API',
    'DESCRIPTION': (
        'Документация API.'
    ),
    'VERSION': f'{VERSION_API}.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

BROKER_TRANSPORT = 'redis'
CELERY_BROKER_URL = f'redis://{DEFAULT_REDIS_HOST}:6379/0'
CELERY_RESULT_BACKEND = f'redis://{DEFAULT_REDIS_HOST}:6379/0'

# CELERY_BROKER_URL = 'redis://redis:6379/0'
# CELERY_RESULT_BACKEND = 'redis://redis:6379/0'

CORS_ALLOW_ALL_ORIGINS = True