# Celery Beat Schedule for Dutchkem Trading AI
# Periodic tasks for indicator calculation, signal generation, and risk monitoring

from celery.schedules import crontab

# ── Configurable symbol list ────────────────────────────────────────────
# Add/remove symbols here; every indicator + signal task fans out over these.
ACTIVE_SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "XAUUSD",
]

# Timeframe → cron interval mapping
TIMEFRAME_SCHEDULE = {
    "M5":  crontab(minute="*/5"),
    "M15": crontab(minute="*/15"),
    "M30": crontab(minute="*/30"),
    "H1":  crontab(minute=0, hour="*/1"),
    "H2":  crontab(minute=0, hour="*/2"),
    "H4":  crontab(minute=0, hour="*/4"),
}


def _build_indicator_tasks() -> dict:
    """Generate indicator-calculation tasks for every active symbol × timeframe."""
    tasks = {}
    for symbol in ACTIVE_SYMBOLS:
        for tf, schedule in TIMEFRAME_SCHEDULE.items():
            key = f"calculate-indicators-{symbol}-{tf.lower()}"
            tasks[key] = {
                "task": "config.tasks.calculate_indicators",
                "schedule": schedule,
                "args": (symbol, tf),
            }
    return tasks


def _build_signal_tasks() -> dict:
    """Generate signal-generation tasks for every active symbol."""
    tasks = {}
    for symbol in ACTIVE_SYMBOLS:
        tasks[f"generate-signals-{symbol.lower()}"] = {
            "task": "config.tasks.generate_signals",
            "schedule": crontab(minute="*/15"),
            "args": (symbol,),
        }
    return tasks


# ── Static (non-symbol-specific) tasks ──────────────────────────────────
STATIC_TASKS = {
    # Monitor drawdown every minute
    "monitor-drawdown": {
        "task": "config.tasks.monitor_drawdown",
        "schedule": crontab(minute="*/1"),
    },
    # Daily risk reset at midnight UTC
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
    # Market data ingestion - every 1 minute for live prices
    "ingest-market-data": {
        "task": "config.tasks.ingest_market_data",
        "schedule": crontab(minute="*/1"),
    },
    # Performance calculation - every 5 minutes
    "calculate-performance": {
        "task": "config.tasks.calculate_performance",
        "schedule": crontab(minute="*/5"),
    },
}

# ── Combined schedule ───────────────────────────────────────────────────
CELERY_BEAT_SCHEDULE = {
    **_build_indicator_tasks(),
    **_build_signal_tasks(),
    **STATIC_TASKS,
}
