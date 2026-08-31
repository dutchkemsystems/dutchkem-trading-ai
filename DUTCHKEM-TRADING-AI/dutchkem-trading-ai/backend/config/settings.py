import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

DEBUG = os.getenv("DEBUG", "1").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
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
    # Local apps
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
    # V2: Scalping Engine
    "scalping",
    # V4: Infrastructure
    "infrastructure",
    # V5: Security Layer
    "security",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # V5: WAF Middleware (before CommonMiddleware to catch bad requests early)
    "security.waf.WAFMiddleware",
    # V5: Zero Trust Middleware (after auth to verify JWT claims)
    "security.zero_trust.ZeroTrustMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
    "config.middleware.RequestTimingMiddleware",
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

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Try PostgreSQL first, fall back to SQLite for development
    DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.postgresql")
    if "sqlite" in DB_ENGINE or os.getenv("USE_SQLITE", "").lower() in ("1", "true"):
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("DB_NAME", "dutchkem_trading"),
                "USER": os.getenv("DB_USER", "dutchkem_admin"),
                "PASSWORD": os.getenv("DB_PASSWORD", ""),
                "HOST": os.getenv("DB_HOST", "localhost"),
                "PORT": os.getenv("DB_PORT", "5432"),
                "CONN_MAX_AGE": 600,
                "OPTIONS": {
                    "connect_timeout": 10,
                },
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
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
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

# JWT Settings
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

# CORS Settings
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
CORS_ALLOW_CREDENTIALS = True

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Channel Layers — use InMemoryChannelLayer when Redis unavailable
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Celery — use memory broker when RabbitMQ unavailable
CELERY_BROKER_URL = os.getenv("RABBITMQ_URL", "memory://")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# InfluxDB
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "dutchkem")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "trading_data")
INFLUXDB_USER = os.getenv("INFLUXDB_USER", "admin")
INFLUXDB_PASSWORD = os.getenv("INFLUXDB_PASSWORD", "")
INFLUXDB_TIMEOUT = int(os.getenv("INFLUXDB_TIMEOUT", 30))

# MetaTrader 5 (SYNX-MT5-MCP or Native Bridge)
MT5_HOST = os.getenv("MT5_HOST", "localhost")
MT5_PORT = int(os.getenv("MT5_PORT", 8082))
MT5_WS_PORT = int(os.getenv("MT5_WS_PORT", 8081))
MT5_TIMEOUT = int(os.getenv("MT5_TIMEOUT", 10))
MT5_MAX_RETRIES = int(os.getenv("MT5_MAX_RETRIES", 5))
MT5_RETRY_DELAY = float(os.getenv("MT5_RETRY_DELAY", 2.0))

# Trading Configuration
TRADING_CONFIG = {
    "MAX_DRAWDOWN": 0.15,
    "MAX_DAILY_LOSS": 0.03,
    "MAX_POSITION_SIZE": 0.02,
    "MAX_OPEN_POSITIONS": 5,
    "MAX_CORRELATION": 0.7,
    "MIN_RISK_REWARD_RATIO": 2.0,
    "TARGET_ANNUAL_GROWTH": 0.40,
}

# Rate Limiting
RATELIMIT_USE_CACHE = "default"
RATELIMIT_FAIL_OPEN = True

# Silence django_ratelimit cache check for development (FileBasedCache doesn't support atomic increment)
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003"]

# Cache — use FileBasedCache (shared across processes) when Redis unavailable
import tempfile
_cache_dir = os.path.join(tempfile.gettempdir(), "dutchkem_cache")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": _cache_dir,
    },
    "sessions": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.path.join(_cache_dir, "sessions"),
    },
    "trading": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.path.join(_cache_dir, "trading"),
    },
}

# Security Settings
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"

# Logging
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
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "propagate": True,
        },
        "trading": {
            "handlers": ["console", "file"],
            "propagate": True,
        },
        "security": {
            "handlers": ["console", "file"],
            "propagate": True,
        },
        "ml": {
            "handlers": ["console", "file"],
            "propagate": True,
        },
        "infrastructure": {
            "handlers": ["console", "file"],
            "propagate": True,
        },
        "scalping": {
            "handlers": ["console", "file"],
            "propagate": True,
        },
    },
}

# ============================================================================
# V5: Military-Grade Security Settings
# ============================================================================

# Zero Trust
ZERO_TRUST_ENABLED = os.getenv("ZERO_TRUST_ENABLED", "1").lower() in ("true", "1", "yes")
ZERO_TRUST_THRESHOLD = int(os.getenv("ZERO_TRUST_THRESHOLD", "60"))
ZERO_TRUST_JWT_SECRET = os.getenv("ZERO_TRUST_JWT_SECRET", SECRET_KEY)

# WAF
WAF_ENABLED = os.getenv("WAF_ENABLED", "1").lower() in ("true", "1", "yes")
WAF_RATE_LIMIT = int(os.getenv("WAF_RATE_LIMIT", "100"))  # requests per minute per IP
WAF_BLOCK_DURATION = int(os.getenv("WAF_BLOCK_DURATION", "3600"))  # seconds
WAF_MAX_BODY_SIZE = int(os.getenv("WAF_MAX_BODY_SIZE", str(10 * 1024 * 1024)))  # 10MB

# IDS/IPS
IDS_ENABLED = os.getenv("IDS_ENABLED", "1").lower() in ("true", "1", "yes")
IDS_BRUTE_FORCE_THRESHOLD = int(os.getenv("IDS_BRUTE_FORCE_THRESHOLD", "5"))
IDS_BRUTE_FORCE_WINDOW = int(os.getenv("IDS_BRUTE_FORCE_WINDOW", "300"))  # seconds

# SIEM
SIEM_ENABLED = os.getenv("SIEM_ENABLED", "1").lower() in ("true", "1", "yes")
SIEM_CORRELATION_WINDOW = int(os.getenv("SIEM_CORRELATION_WINDOW", "300"))  # seconds

# RASP
RASP_ENABLED = os.getenv("RASP_ENABLED", "1").lower() in ("true", "1", "yes")
RASP_INTEGRITY_CHECK_INTERVAL = int(os.getenv("RASP_INTEGRITY_CHECK_INTERVAL", "3600"))

# Encryption
ENCRYPTION_KEY_VERSION = int(os.getenv("ENCRYPTION_KEY_VERSION", "1"))
ENCRYPTION_ALGORITHM = os.getenv("ENCRYPTION_ALGORITHM", "AES-256-GCM")

# Credential Manager
CREDENTIAL_VAULT_ENABLED = os.getenv("CREDENTIAL_VAULT_ENABLED", "1").lower() in ("true", "1", "yes")

# ============================================================================
# V6: Advanced Enhancement Settings
# ============================================================================

# Meta-Learning
META_LEARNING_ENABLED = os.getenv("META_LEARNING_ENABLED", "1").lower() in ("true", "1", "yes")
META_LEARNING_ADAPTATION_THRESHOLD = float(os.getenv("META_LEARNING_ADAPTATION_THRESHOLD", "0.95"))

# Asset Ensemble
ASSET_ENSEMBLE_ENABLED = os.getenv("ASSET_ENSEMBLE_ENABLED", "1").lower() in ("true", "1", "yes")

# Transfer Learning
TRANSFER_LEARNING_ENABLED = os.getenv("TRANSFER_LEARNING_ENABLED", "1").lower() in ("true", "1", "yes")

# Dynamic Allocation
DYNAMIC_ALLOCATION_ENABLED = os.getenv("DYNAMIC_ALLOCATION_ENABLED", "1").lower() in ("true", "1", "yes")
DYNAMIC_ALLOCATION_MIN_WEIGHT = float(os.getenv("DYNAMIC_ALLOCATION_MIN_WEIGHT", "0.01"))
DYNAMIC_ALLOCATION_MAX_WEIGHT = float(os.getenv("DYNAMIC_ALLOCATION_MAX_WEIGHT", "0.25"))

# Correlation Manager
CORRELATION_THRESHOLD = float(os.getenv("CORRELATION_THRESHOLD", "0.70"))
CORRELATION_LOOKBACK = int(os.getenv("CORRELATION_LOOKBACK", "50"))

# Time-Based Exit
TIME_EXIT_SCALP_MINUTES = int(os.getenv("TIME_EXIT_SCALP_MINUTES", "30"))
TIME_EXIT_SWING_MINUTES = int(os.getenv("TIME_EXIT_SWING_MINUTES", "180"))
TIME_EXIT_TREND_MINUTES = int(os.getenv("TIME_EXIT_TREND_MINUTES", "720"))

# Execution Optimizer
MAX_SLIPPAGE_PIPS = float(os.getenv("MAX_SLIPPAGE_PIPS", "0.5"))
MAX_SPREAD_PIPS = float(os.getenv("MAX_SPREAD_PIPS", "0.5"))

# Scalping Scanner
SCANNER_MAX_WORKERS = int(os.getenv("SCANNER_MAX_WORKERS", "8"))

# Strategy Diversification
STRATEGY_DIVERSIFICATION_ENABLED = os.getenv("STRATEGY_DIVERSIFICATION_ENABLED", "1").lower() in ("true", "1", "yes")

# Infrastructure
MULTI_NODE_ENABLED = os.getenv("MULTI_NODE_ENABLED", "0").lower() in ("true", "1", "yes")
SELF_HEALING_ENABLED = os.getenv("SELF_HEALING_ENABLED", "1").lower() in ("true", "1", "yes")
MT5_POOL_MAX_CONNECTIONS = int(os.getenv("MT5_POOL_MAX_CONNECTIONS", "5"))
