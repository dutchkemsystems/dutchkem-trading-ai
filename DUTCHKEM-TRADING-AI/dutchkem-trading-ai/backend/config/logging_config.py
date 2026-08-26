# Dutchkem Trading AI — Structured Logging Configuration

import logging
import logging.config
import sys

from pythonjsonlogger import jsonlogger

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "rename_fields": {
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        },
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
        "request_context": {
            "()": "logging_filters.RequestContextFilter",
        },
        "trading_context": {
            "()": "logging_filters.TradingContextFilter",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": sys.stdout,
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/django.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "json",
        },
        "trading_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/trading.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 10,
            "formatter": "json",
        },
        "risk_file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/risk.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 10,
            "formatter": "json",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/error.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 10,
            "formatter": "json",
        },
        "security_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/security.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 10,
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "security_file"],
            "level": "INFO",
            "propagate": False,
        },
        "trading": {
            "handlers": ["console", "trading_file"],
            "level": "INFO",
            "propagate": False,
            "filters": ["trading_context"],
        },
        "risk_management": {
            "handlers": ["console", "risk_file"],
            "level": "WARNING",
            "propagate": False,
            "filters": ["trading_context"],
        },
        "signals": {
            "handlers": ["console", "trading_file"],
            "level": "INFO",
            "propagate": False,
            "filters": ["trading_context"],
        },
        "payments": {
            "handlers": ["console", "security_file"],
            "level": "INFO",
            "propagate": False,
            "filters": ["request_context"],
        },
        "accounts": {
            "handlers": ["console", "security_file"],
            "level": "INFO",
            "propagate": False,
            "filters": ["request_context"],
        },
        "mcp_integration": {
            "handlers": ["console", "trading_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "error_file"],
        "level": "INFO",
    },
}
