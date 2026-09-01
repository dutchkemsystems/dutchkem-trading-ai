from rest_framework import serializers

from .models import EconomicCalendar, LivePrice, MarketData, MarketSentiment


class MarketDataSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)
    timeframe_code = serializers.CharField(source="timeframe.code", read_only=True)

    class Meta:
        model = MarketData
        fields = [
            "id",
            "symbol",
            "symbol_name",
            "timeframe",
            "timeframe_code",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "tick_volume",
            "spread",
        ]


class LivePriceSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)

    class Meta:
        model = LivePrice
        fields = ["id", "symbol", "symbol_name", "bid", "ask", "spread", "last_update"]


class EconomicCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = EconomicCalendar
        fields = [
            "id",
            "event_name",
            "country",
            "currency",
            "impact_level",
            "scheduled_time",
            "actual_value",
            "forecast_value",
            "previous_value",
            "description",
        ]


class MarketSentimentSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)

    class Meta:
        model = MarketSentiment
        fields = [
            "id",
            "symbol",
            "symbol_name",
            "timestamp",
            "sentiment_score",
            "fear_greed_index",
            "news_sentiment",
            "social_sentiment",
            "institutional_flow",
            "data_sources",
        ]
