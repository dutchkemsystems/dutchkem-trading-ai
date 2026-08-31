from django.contrib import admin

from .models import EconomicCalendar, LivePrice, MarketData, MarketSentiment


@admin.register(MarketData)
class MarketDataAdmin(admin.ModelAdmin):
    list_display = ["symbol", "timeframe", "timestamp", "open", "high", "low", "close", "volume"]
    list_filter = ["timeframe"]
    search_fields = ["symbol__name"]
    date_hierarchy = "timestamp"


@admin.register(LivePrice)
class LivePriceAdmin(admin.ModelAdmin):
    list_display = ["symbol", "bid", "ask", "spread", "last_update"]
    search_fields = ["symbol__name"]


@admin.register(EconomicCalendar)
class EconomicCalendarAdmin(admin.ModelAdmin):
    list_display = [
        "event_name",
        "country",
        "currency",
        "impact_level",
        "scheduled_time",
        "actual_value",
        "forecast_value",
    ]
    list_filter = ["impact_level", "currency"]
    search_fields = ["event_name"]
    date_hierarchy = "scheduled_time"


@admin.register(MarketSentiment)
class MarketSentimentAdmin(admin.ModelAdmin):
    list_display = ["symbol", "sentiment_score", "fear_greed_index", "news_sentiment", "social_sentiment", "timestamp"]
    list_filter = ["symbol"]
    date_hierarchy = "timestamp"
