from rest_framework import serializers

from .models import (
    CorrelationMatrix,
    DailyPerformance,
    DrawdownMonitor,
    PositionSizing,
    RiskAlert,
    RiskParameter,
)


class RiskParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskParameter
        fields = [
            "id",
            "name",
            "max_drawdown",
            "max_daily_loss",
            "max_position_size",
            "max_open_positions",
            "max_correlation",
            "min_risk_reward_ratio",
            "daily_growth_target",
            "daily_target_lock",
            "max_daily_trades",
            "target_daily_growth",
            "target_monthly_growth",
            "target_annual_growth",
            "is_active",
            "created_at",
            "updated_at",
        ]


class PositionSizingSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)
    timeframe_code = serializers.CharField(source="timeframe.code", read_only=True)

    class Meta:
        model = PositionSizing
        fields = [
            "id",
            "user",
            "symbol",
            "symbol_name",
            "timeframe",
            "timeframe_code",
            "risk_per_trade",
            "account_equity",
            "risk_amount",
            "stop_loss_pips",
            "position_size",
            "daily_pnl",
            "daily_trades_count",
            "remaining_daily_budget",
            "calculated_at",
        ]
        read_only_fields = ["id", "user", "calculated_at"]


class DrawdownMonitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrawdownMonitor
        fields = [
            "id",
            "user",
            "peak_equity",
            "current_equity",
            "starting_equity_today",
            "drawdown_percent",
            "daily_pnl",
            "daily_pnl_percent",
            "daily_loss_percent",
            "daily_trades_count",
            "is_circuit_breaker_triggered",
            "is_daily_loss_triggered",
            "is_drawdown_triggered",
            "is_daily_target_triggered",
            "is_max_trades_triggered",
            "triggered_at",
            "daily_reset_at",
            "created_at",
            "updated_at",
        ]


class CorrelationMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrelationMatrix
        fields = ["id", "symbol_pair", "correlation", "timeframe", "calculated_at"]


class RiskAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAlert
        fields = ["id", "user", "alert_type", "severity", "message", "data", "is_read", "created_at"]


class DailyPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyPerformance
        fields = [
            "id",
            "user",
            "date",
            "starting_equity",
            "ending_equity",
            "daily_pnl",
            "daily_pnl_percent",
            "total_trades",
            "winning_trades",
            "losing_trades",
            "win_rate",
            "total_profit",
            "total_loss",
            "avg_win",
            "avg_loss",
            "max_drawdown",
            "risk_reward_ratio",
            "timeframe_performance",
            "created_at",
        ]


class PositionSizeCalculateSerializer(serializers.Serializer):
    symbol = serializers.UUIDField()
    timeframe = serializers.CharField(max_length=5, required=False)
    stop_loss_pips = serializers.IntegerField()
    risk_per_trade = serializers.DecimalField(max_digits=5, decimal_places=2, default=1.0)
