from rest_framework import serializers

from .models import GoldEdgeBacktest, GoldEdgeConfig, GoldEdgeSignal


class GoldEdgeConfigSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)
    timeframe_code = serializers.CharField(source="timeframe.code", read_only=True)

    class Meta:
        model = GoldEdgeConfig
        fields = [
            "id",
            "name",
            "symbol",
            "symbol_name",
            "timeframe",
            "timeframe_code",
            "momentum_weight",
            "trend_weight",
            "volatility_weight",
            "dxy_correlation_weight",
            "atr_period",
            "ema_period",
            "atr_multipliers",
            "atr_ratio_min",
            "atr_ratio_max",
            "min_gec_score",
            "min_combined_score",
            "risk_per_trade",
            "sl_atr_multiplier",
            "tp_atr_multiplier",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GoldEdgeSignalSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)
    timeframe_code = serializers.CharField(source="timeframe.code", read_only=True)
    config_name = serializers.CharField(source="config.name", read_only=True)

    class Meta:
        model = GoldEdgeSignal
        fields = [
            "id",
            "config",
            "config_name",
            "symbol",
            "symbol_name",
            "timeframe",
            "timeframe_code",
            "direction",
            "gec_score",
            "combined_matrix_score",
            "momentum_score",
            "trend_score",
            "volatility_score",
            "dxy_correlation_score",
            "atr_border_layer",
            "atr_ratio",
            "atr_filter_pass",
            "entry_price",
            "stop_loss",
            "take_profit",
            "risk_reward_ratio",
            "confidence",
            "is_active",
            "generated_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class GoldEdgeBacktestSerializer(serializers.ModelSerializer):
    config_name = serializers.CharField(source="config.name", read_only=True, default="")

    class Meta:
        model = GoldEdgeBacktest
        fields = [
            "id",
            "config",
            "config_name",
            "name",
            "status",
            "start_date",
            "end_date",
            "initial_balance",
            "final_balance",
            "total_pnl",
            "total_pnl_percent",
            "total_trades",
            "winning_trades",
            "losing_trades",
            "win_rate",
            "profit_factor",
            "max_drawdown",
            "sharpe_ratio",
            "parameters",
            "trades",
            "equity_curve",
            "gec_scores_over_time",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GoldEdgeAnalysisRequestSerializer(serializers.Serializer):
    """Request serializer for on-demand Gold Edge analysis."""
    symbol = serializers.CharField(max_length=20)
    timeframe = serializers.CharField(max_length=5, default="H1")
    config_id = serializers.UUIDField(required=False, allow_null=True)


class GoldEdgeScanRequestSerializer(serializers.Serializer):
    """Request scanner for batch Gold Edge analysis."""
    symbols = serializers.ListField(
        child=serializers.CharField(max_length=20),
        min_length=1,
        max_length=20,
    )
    timeframe = serializers.CharField(max_length=5, default="H1")
    config_id = serializers.UUIDField(required=False, allow_null=True)
