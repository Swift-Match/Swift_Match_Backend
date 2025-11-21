import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
from celery.schedules import crontab

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-secret-key")
DEBUG = False

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_yasg",
    "drf_spectacular",
    "infrastructure.rest",
    "apps.users.apps.UsersConfig",
    "apps.albums.apps.AlbumsConfig",
    "apps.tracks.apps.TracksConfig",
    "apps.rankings.apps.RankingsConfig",
    "apps.social.apps.SocialConfig",
    'django_celery_beat',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",     
    "django.contrib.messages.middleware.MessageMiddleware",        
]

ROOT_URLCONF = "config.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "swift_match_db"),
        "USER": os.getenv("POSTGRES_USER", "swift_admin"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "swift_pass"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Swift Match API",
    "DESCRIPTION": "API da aplicação SwiftMatch",
    "VERSION": "1.0.0",
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  
        "APP_DIRS": True, 
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK.update({
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
})

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60), # Token expira em 60 min
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),   # Token de refresh dura 1 dia
    "ROTATE_REFRESH_TOKENS": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


CELERY_BROKER_URL = 'redis://swift_redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://swift_redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'

CELERY_BEAT_SCHEDULE = {
    'update-global-ranking-daily': {
        # O caminho para a função que criamos
        'task': 'apps.rankings.tasks.run_global_ranking_calculation', 
        # Roda todos os dias à meia-noite (00:00)
        'schedule': crontab(minute=0, hour=0), 
        'args': (),
        'options': {'queue': 'default'}
    },
}
