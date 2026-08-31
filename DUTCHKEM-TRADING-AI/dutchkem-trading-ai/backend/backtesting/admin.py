from django.contrib import admin

from .models import BacktestResult


@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = ["name", "symbol", "timeframe", "strategy", "total_pnl", "win_rate", "created_at"]
    list_filter = ["strategy", "timeframe"]
    search_fields = ["name", "symbol"]
