from django.contrib import admin

from .models import EABacktestResult, EADeployment, ExpertAdvisor


@admin.register(ExpertAdvisor)
class ExpertAdvisorAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "user",
        "symbol",
        "timeframe",
        "status",
        "total_trades",
        "winning_trades",
        "total_profit",
        "ai_generated",
        "deployed_at",
    ]
    list_filter = ["status", "timeframe", "ai_generated"]
    search_fields = ["name", "user__username", "symbol__name"]
    date_hierarchy = "created_at"


@admin.register(EABacktestResult)
class EABacktestResultAdmin(admin.ModelAdmin):
    list_display = [
        "ea",
        "start_date",
        "end_date",
        "initial_balance",
        "final_balance",
        "total_return",
        "max_drawdown",
        "sharpe_ratio",
        "total_trades",
    ]
    list_filter = ["ea"]
    date_hierarchy = "created_at"


@admin.register(EADeployment)
class EADeploymentAdmin(admin.ModelAdmin):
    list_display = ["ea", "mt5_account", "mt5_server", "status", "deployed_at", "stopped_at"]
    list_filter = ["status"]
    search_fields = ["mt5_account", "ea__name"]
    date_hierarchy = "deployed_at"
