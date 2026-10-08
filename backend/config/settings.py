"""Django settings for the Dars Jadvali project. All secrets come from the environment."""

import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(int(default))).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-only")
# Pin "today" for the demo semester (YYYY-MM-DD or YYYY-MM-DDTHH:MM); empty = real time.
DEMO_NOW = os.environ.get("DEMO_NOW", "")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",") if h]

INSTALLED_APPS = [
    # modeltranslation must come before django.contrib.admin
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.academics",
    "apps.scheduling",
    "apps.solver",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "dars_jadvali"),
        "USER": os.environ.get("POSTGRES_USER", "dars"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

# --- Internationalisation -------------------------------------------------
# UI language (uz/ru/en) is independent of a group's teaching language.
LANGUAGE_CODE = "uz"
LANGUAGES = [
    ("uz", _("Uzbek")),
    ("ru", _("Russian")),
    ("en", _("English")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

MODELTRANSLATION_DEFAULT_LANGUAGE = "uz"
MODELTRANSLATION_LANGUAGES = ("uz", "ru", "en")
MODELTRANSLATION_FALLBACK_LANGUAGES = {"default": ("uz",)}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- API ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.Pagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,  # shown on the profile page
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Dars Jadvali API",
    "DESCRIPTION": "Academy timetable automation system",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Celery ---------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULE = {
    "lesson-reminders": {"task": "notifications.reminders", "schedule": 60.0},
    "evening-summary": {
        "task": "notifications.daily_digest",
        "schedule": crontab(hour=20, minute=0),
    },
}

# --- Web Push ---------------------------------------------------------------
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "")

# --- Academy rules (see docs/ASSUMPTIONS.md) --------------------------------
GROUP_NAME_PATTERN = os.environ.get("GROUP_NAME_PATTERN", "{prefix}-{course}{number:02d}")
