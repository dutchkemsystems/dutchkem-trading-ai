# Celery Beat Schedule for Dutchkem Trading AI
# Periodic tasks for indicator calculation, signal generation, and risk monitoring

from celery.schedules import crontab

# ── Configurable symbol list ────────────────────────────────────────
# Use V6 MarketScanner defaults when available; fall back to static list.
try:
    from ml.market_scanner import MarketScanner
    ACTIVE_SYMBOLS = list(MarketScanner.DEFAULT_SYMBOLS)
except ImportError:
    ACTIVE_SYMBOLS = [
        # Majors (7)
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
        # Crosses (7)
        "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "EURCHF", "GBPCAD",
        # Exotics (4)
        "USDTRY", "USDZAR", "USDMXN", "USDCNH",
        # Metals (3)
        "XAUUSD", "XAGUSD", "XAUEUR",
        # Crypto (3)
        "BTCUSD", "ETHUSD", "SOLUSD",
        # Indices (4)
        "US30", "US500", "NAS100", "GER40",
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
    # ── V6.5 Complete Trading Cycle (PRIMARY) — runs every 60 seconds ─
    "run-v65-trading-cycle": {
        "task": "config.tasks.run_v6_trading_cycle",
        "schedule": 60.0,
    },
    # ── V6.5 Backup Trading Cycle — runs every 90 seconds ─────────
    # Handles fallback when V6.5 fails. Uses BackupManager to determine system.
    "run-backup-trading-cycle": {
        "task": "config.tasks.run_backup_trading_cycle",
        "schedule": 90.0,  # Every 90 seconds (offset from main cycle)
    },
    # ── V6.5 Self-Optimization — runs every 24 hours ──────────────
    "run-v6-optimization": {
        "task": "config.tasks.run_v6_optimization",
        "schedule": crontab(minute=0, hour=3),  # 03:00 UTC daily
    },
    # ── V6.5 Profit Target Management — runs every 60 seconds ─────
    # COMPULSORY: V6.5 determines ALL profit targets dynamically.
    # This task syncs RiskParameter with V6.5 computed targets and
    # ensures DrawdownMonitor uses V6.5's target values.
    "v65-manage-profit-targets": {
        "task": "config.tasks.v65_manage_profit_targets",
        "schedule": 60.0,  # Every 60 seconds, same as trading cycle
    },
    # ── V6.5 Backup System Health Check — runs every 5 minutes ────
    # Monitors health of all backup trading systems.
    "check-backup-system-health": {
        "task": "config.tasks.check_backup_system_health",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}

# ── Combined schedule ───────────────────────────────────────────────────
CELERY_BEAT_SCHEDULE = {
    **_build_indicator_tasks(),
    **_build_signal_tasks(),
    **STATIC_TASKS,
}
