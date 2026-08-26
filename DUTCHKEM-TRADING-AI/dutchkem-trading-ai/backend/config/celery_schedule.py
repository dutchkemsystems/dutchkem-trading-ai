# Celery Beat Schedule for Dutchkem Trading AI
# Periodic tasks for indicator calculation, signal generation, and risk monitoring

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Calculate indicators every 5 minutes
    "calculate-indicators-5m": {
        "task": "config.tasks.calculate_indicators",
        "schedule": crontab(minute="*/5"),
        "args": ("EURUSD", "M5"),
    },
    "calculate-indicators-15m": {
        "task": "config.tasks.calculate_indicators",
        "schedule": crontab(minute="*/15"),
        "args": ("EURUSD", "M15"),
    },
    "calculate-indicators-30m": {
        "task": "config.tasks.calculate_indicators",
        "schedule": crontab(minute="*/30"),
        "args": ("EURUSD", "M30"),
    },
    "calculate-indicators-1h": {
        "task": "config.tasks.calculate_indicators",
        "schedule": crontab(minute=0, hour="*/1"),
        "args": ("EURUSD", "H1"),
    },
    "calculate-indicators-2h": {
        "task": "config.tasks.calculate_indicators",
        "schedule": crontab(minute=0, hour="*/2"),
        "args": ("EURUSD", "H2"),
    },
    "calculate-indicators-4h": {
        "task": "config.tasks.calculate_indicators",
        "schedule": crontab(minute=0, hour="*/4"),
        "args": ("EURUSD", "H4"),
    },
    # Generate signals every 15 minutes
    "generate-signals": {
        "task": "config.tasks.generate_signals",
        "schedule": crontab(minute="*/15"),
        "args": ("EURUSD",),
    },
    # Monitor drawdown every minute
    "monitor-drawdown": {
        "task": "config.tasks.monitor_drawdown",
        "schedule": crontab(minute="*/1"),
    },
    # Reset daily counters at midnight UTC
    "reset-daily-counters": {
        "task": "config.tasks.reset_daily_counters",
        "schedule": crontab(minute=0, hour=0),
    },
    # Sync MT5 data every 5 minutes
    "sync-mt5-data": {
        "task": "config.tasks.sync_mt5_data",
        "schedule": crontab(minute="*/5"),
    },
    # Health check every 30 seconds
    "health-check": {
        "task": "config.tasks.health_check",
        "schedule": 30.0,
    },
}
