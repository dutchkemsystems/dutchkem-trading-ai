from django.contrib import admin

from .models import CachedDailyPerformance, CachedSymbolBreakdown, CachedTradeSummary


@admin.register(CachedTradeSummary)
class CachedTradeSummaryAdmin(admin.ModelAdmin):
    list_display = ["user", "period", "total_trades", "win_rate", "total_pnl", "profit_factor", "cached_at"]
    list_filter = ["period"]
    search_fields = ["user__username"]
    date_hierarchy = "cached_at"


@admin.register(CachedDailyPerformance)
class CachedDailyPerformanceAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "daily_pnl", "daily_pnl_percent", "total_trades", "win_rate", "cached_at"]
    list_filter = ["date"]
    search_fields = ["user__username"]
    date_hierarchy = "date"


@admin.register(CachedSymbolBreakdown)
class CachedSymbolBreakdownAdmin(admin.ModelAdmin):
    list_display = ["user", "symbol_name", "total_pnl", "total_trades", "win_rate", "period", "cached_at"]
    list_filter = ["period", "symbol_name"]
    search_fields = ["user__username", "symbol_name"]
    date_hierarchy = "cached_at"
