from django.contrib import admin

from .models import (
    Indicator,
    IndicatorCategory,
    IndicatorValue,
    Timeframe,
    TimeframeIndicatorConfig,
)


@admin.register(Timeframe)
class TimeframeAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "minutes",
        "strategy_type",
        "risk_level",
        "target_pips_min",
        "target_pips_max",
        "is_active",
    ]
    list_filter = ["risk_level", "is_active"]
    search_fields = ["code", "name"]


@admin.register(IndicatorCategory)
class IndicatorCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name"]


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ["name", "display_name", "category", "indicator_type", "is_active"]
    list_filter = ["category", "indicator_type", "is_active"]
    search_fields = ["name", "display_name"]
    filter_horizontal = ["suitable_timeframes"]


@admin.register(IndicatorValue)
class IndicatorValueAdmin(admin.ModelAdmin):
    list_display = ["symbol", "indicator", "timeframe", "timestamp", "signal"]
    list_filter = ["signal", "timeframe"]
    search_fields = ["symbol__name", "indicator__name"]
    date_hierarchy = "timestamp"


@admin.register(TimeframeIndicatorConfig)
class TimeframeIndicatorConfigAdmin(admin.ModelAdmin):
    list_display = ["timeframe", "indicator", "weight", "priority"]
    list_filter = ["timeframe"]
    search_fields = ["indicator__name"]
