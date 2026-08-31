LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
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
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/django.log",
            "maxBytes": 10485760,
            "backupCount": 10,
            "formatter": "json",
        },
        "trading_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/trading.log",
            "maxBytes": 10485760,
            "backupCount": 10,
            "formatter": "json",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/error.log",
            "maxBytes": 10485760,
            "backupCount": 10,
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "propagate": True,
            "level": "WARNING",
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "propagate": False,
            "level": "INFO",
        },
        "trading": {
            "handlers": ["console", "trading_file"],
            "propagate": False,
            "level": "INFO",
        },
        "signals": {
            "handlers": ["console", "trading_file"],
            "propagate": False,
            "level": "INFO",
        },
        "risk_management": {
            "handlers": ["console", "trading_file"],
            "propagate": False,
            "level": "INFO",
        },
        "payments": {
            "handlers": ["console", "file"],
            "propagate": False,
            "level": "INFO",
        },
        "market_data": {
            "handlers": ["console", "file"],
            "propagate": False,
            "level": "INFO",
        },
        "notifications": {
            "handlers": ["console", "file"],
            "propagate": False,
            "level": "INFO",
        },
        "monitoring": {
            "handlers": ["console"],
            "propagate": False,
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["console", "error_file"],
        "level": "INFO",
    },
}
