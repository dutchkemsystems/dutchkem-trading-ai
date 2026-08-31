from django.contrib import admin

from .models import (
    CorrelationMatrix,
    DailyPerformance,
    DrawdownMonitor,
    PositionSizing,
    RiskAlert,
    RiskParameter,
    TradingSettings,
)


@admin.register(RiskParameter)
class RiskParameterAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "max_drawdown",
        "max_daily_loss",
        "max_position_size",
        "max_daily_trades",
        "daily_growth_target",
        "is_active",
    ]
    list_filter = ["is_active"]


@admin.register(PositionSizing)
class PositionSizingAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "symbol",
        "timeframe",
        "risk_per_trade",
        "account_equity",
        "position_size",
        "daily_trades_count",
        "calculated_at",
    ]
    list_filter = ["timeframe"]
    search_fields = ["user__username", "symbol__name"]
    date_hierarchy = "calculated_at"


@admin.register(DrawdownMonitor)
class DrawdownMonitorAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "current_equity",
        "drawdown_percent",
        "daily_pnl_percent",
        "daily_trades_count",
        "is_circuit_breaker_triggered",
        "updated_at",
    ]
    list_filter = ["is_circuit_breaker_triggered", "is_daily_loss_triggered", "is_drawdown_triggered"]
    search_fields = ["user__username"]
    date_hierarchy = "updated_at"


@admin.register(CorrelationMatrix)
class CorrelationMatrixAdmin(admin.ModelAdmin):
    list_display = ["symbol_pair", "correlation", "timeframe", "calculated_at"]
    list_filter = ["timeframe"]
    date_hierarchy = "calculated_at"


@admin.register(RiskAlert)
class RiskAlertAdmin(admin.ModelAdmin):
    list_display = ["user", "alert_type", "severity", "is_read", "created_at"]
    list_filter = ["alert_type", "severity", "is_read"]
    search_fields = ["user__username"]
    date_hierarchy = "created_at"


@admin.register(DailyPerformance)
class DailyPerformanceAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "daily_pnl", "daily_pnl_percent", "total_trades", "win_rate", "risk_reward_ratio"]
    list_filter = ["date"]
    search_fields = ["user__username"]
    date_hierarchy = "date"


@admin.register(TradingSettings)
class TradingSettingsAdmin(admin.ModelAdmin):
    list_display = ["name", "trading_mode", "max_spread_pips", "max_slippage_pips", "min_confidence", "is_active"]
    list_filter = ["trading_mode", "is_active"]
    fieldsets = (
        ("Trading Mode", {
            "fields": ("name", "trading_mode", "is_active"),
        }),
        ("Execution Limits", {
            "fields": ("max_spread_pips", "max_slippage_pips", "min_confidence"),
        }),
        ("Symbols", {
            "fields": ("active_symbols",),
        }),
    )
