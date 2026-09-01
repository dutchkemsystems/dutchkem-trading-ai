from rest_framework import serializers

from .models import ConfluenceScore, Signal, SignalHistory


class SignalSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)
    timeframe_code = serializers.CharField(source="timeframe.code", read_only=True)

    class Meta:
        model = Signal
        fields = [
            "id",
            "symbol",
            "symbol_name",
            "timeframe",
            "timeframe_code",
            "signal_type",
            "strength",
            "confluence_score",
            "indicator_agreement",
            "pattern_detected",
            "entry_price",
            "stop_loss",
            "take_profit",
            "risk_reward_ratio",
            "h4_trend",
            "h1_trend",
            "m15_trend",
            "mtf_confluence_score",
            "generated_by",
            "confidence",
            "is_active",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SignalHistorySerializer(serializers.ModelSerializer):
    signal_type = serializers.CharField(source="signal.signal_type", read_only=True)
    symbol_name = serializers.CharField(source="signal.symbol.name", read_only=True)

    class Meta:
        model = SignalHistory
        fields = [
            "id",
            "signal",
            "signal_type",
            "symbol_name",
            "outcome",
            "actual_pips",
            "max_favorable",
            "max_adverse",
            "closed_at",
        ]


class ConfluenceScoreSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)

    class Meta:
        model = ConfluenceScore
        fields = [
            "id",
            "symbol",
            "symbol_name",
            "timestamp",
            "m5_score",
            "m15_score",
            "m30_score",
            "h1_score",
            "h2_score",
            "h4_score",
            "total_score",
            "direction",
            "higher_tf_agreement",
            "all_tf_aligned",
        ]


class SignalGenerateSerializer(serializers.Serializer):
    symbol = serializers.UUIDField()
    timeframe = serializers.CharField(max_length=5)
