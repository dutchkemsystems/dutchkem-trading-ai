from django.contrib import admin

from .models import ConfluenceScore, Signal, SignalHistory


@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = [
        "symbol",
        "timeframe",
        "signal_type",
        "strength",
        "confluence_score",
        "mtf_confluence_score",
        "is_active",
        "created_at",
    ]
    list_filter = ["signal_type", "timeframe", "is_active"]
    search_fields = ["symbol__name"]
    date_hierarchy = "created_at"


@admin.register(SignalHistory)
class SignalHistoryAdmin(admin.ModelAdmin):
    list_display = ["signal", "outcome", "actual_pips", "max_favorable", "max_adverse", "closed_at"]
    list_filter = ["outcome"]
    date_hierarchy = "closed_at"


@admin.register(ConfluenceScore)
class ConfluenceScoreAdmin(admin.ModelAdmin):
    list_display = ["symbol", "total_score", "direction", "higher_tf_agreement", "all_tf_aligned", "timestamp"]
    list_filter = ["direction", "higher_tf_agreement", "all_tf_aligned"]
    search_fields = ["symbol__name"]
    date_hierarchy = "timestamp"
