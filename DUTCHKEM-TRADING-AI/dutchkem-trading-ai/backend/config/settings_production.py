import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = False

# Render / generic: Parse ALLOWED_HOSTS from comma-separated string
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
# Add Render default hostname if not explicitly set
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
# Support legacy Fly.io env if still present
FLY_APP_NAME = os.environ.get("FLY_APP_NAME", "")
if FLY_APP_NAME:
    ALLOWED_HOSTS.extend([
        f"{FLY_APP_NAME}.fly.dev",
        f"{FLY_APP_NAME}.internal",
        ".fly.dev",
        ".internal",
    ])
# Railway: Add Railway domain if RAILWAY_PUBLIC_DOMAIN is set
RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
if RAILWAY_PUBLIC_DOMAIN and RAILWAY_PUBLIC_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_yasg",
    "channels",
    "django_celery_beat",
    "django_celery_results",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "django_ratelimit",
    "accounts",
    "trading",
    "indicators",
    "signals",
    "risk_management",
    "payments",
    "expert_advisors",
    "mcp_integration",
    "market_data",
    "notifications",
    "analytics",
    "referrals",
    "backtesting",
    "ml",
    "gold_edge",
    "audit",
    "scalping",
    "infrastructure",
    "security",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "security.waf.WAFMiddleware",
    "security.zero_trust.ZeroTrustMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

REDIS_URL = os.environ.get("REDIS_URL", "")

# Only use Redis channel layer if Redis is available
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )
}

# Use Redis cache if available, otherwise fall back to local memory
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "KEY_PREFIX": "dutchkem",
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise configuration for cloud deployment (Render / Fly.io / Railway)
# Enables efficient static file serving with compression and caching
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# WhiteNoise settings
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False  # Disable in production for better performance
WHITENOISE_MAX_AGE = 31536000  # 1 year cache for static files

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "accounts.serializers.CustomTokenObtainPairSerializer",
}

CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
# Add Render frontend domain if hostname is set
if RENDER_EXTERNAL_HOSTNAME:
    backend_url = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if backend_url not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(backend_url)
# Add Fly.io frontend domain if app name is set (legacy support)
if FLY_APP_NAME:
    CORS_ALLOWED_ORIGINS.extend([
        f"https://{FLY_APP_NAME}-frontend.fly.dev",
        "http://localhost:3000",
    ])
# Railway: Add Railway public domain if set
if RAILWAY_PUBLIC_DOMAIN:
    railway_backend_url = f"https://{RAILWAY_PUBLIC_DOMAIN}"
    if railway_backend_url not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(railway_backend_url)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
# Add Render frontend domain if hostname is set
if RENDER_EXTERNAL_HOSTNAME:
    backend_url = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if backend_url not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(backend_url)
# Add Fly.io frontend domain if app name is set (legacy support)
if FLY_APP_NAME:
    CSRF_TRUSTED_ORIGINS.extend([
        f"https://{FLY_APP_NAME}-frontend.fly.dev",
        "http://localhost:3000",
    ])
# Railway: Add Railway public domain if set
if RAILWAY_PUBLIC_DOMAIN:
    railway_backend_url = f"https://{RAILWAY_PUBLIC_DOMAIN}"
    if railway_backend_url not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(railway_backend_url)

# Celery: Use Redis if available, otherwise disable
if REDIS_URL:
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = "django-db"
else:
    CELERY_BROKER_URL = None
    CELERY_RESULT_BACKEND = None
    CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously without broker
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60

INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "dutchkem")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "trading_data")

MT5_HOST = os.environ.get("MT5_HOST", "localhost")
MT5_PORT = int(os.environ.get("MT5_PORT", 3000))
MT5_WS_PORT = int(os.environ.get("MT5_WS_PORT", 3001))
MT5_TIMEOUT = int(os.environ.get("MT5_TIMEOUT", 10))
MT5_MAX_RETRIES = int(os.environ.get("MT5_MAX_RETRIES", 5))
MT5_RETRY_DELAY = float(os.environ.get("MT5_RETRY_DELAY", 2.0))

# MT5 MCP Bridge URL (Cloudflare Tunnel endpoint)
MT5_MCP_URL = os.environ.get("MT5_MCP_URL", "http://localhost:8080")

KORA_SECRET_KEY = os.environ.get("KORA_SECRET_KEY", "")
KORA_ENCRYPTION_KEY = os.environ.get("KORA_ENCRYPTION_KEY", "")
KORA_BASE_URL = os.environ.get("KORA_BASE_URL", "https://api.korapay.com/merchant/api/v1")
KORA_PUBLIC_KEY = os.environ.get("KORA_PUBLIC_KEY", "")
KORA_WEBHOOK_SECRET = os.environ.get("KORA_WEBHOOK_SECRET", "")

TRADING_CONFIG = {
    "MAX_DRAWDOWN": 0.15,
    "MAX_DAILY_LOSS": 0.03,
    "MAX_POSITION_SIZE": 0.02,
    "MAX_OPEN_POSITIONS": 5,
    "MAX_CORRELATION": 0.7,
    "MIN_RISK_REWARD_RATIO": 2.0,
    "TARGET_ANNUAL_GROWTH": 0.40,
}

RATELIMIT_USE_CACHE = "default"
RATELIMIT_FAIL_OPEN = True

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(levelname)s %(asctime)s %(module)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "json_console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
        "trading": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "payments": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "signals": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "risk_management": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "infrastructure": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "infrastructure.failover": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "infrastructure.health_monitor": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "infrastructure.alert_system": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Render / Production: Use JSON logging for cloud environments
        "cloud": {
            "handlers": ["json_console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Cloud Health Check Configuration (Render / Fly.io / Railway)
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_TIMEOUT = 10
