from rest_framework import serializers

from .models import EABacktestResult, EADeployment, ExpertAdvisor


class ExpertAdvisorSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)
    timeframe_code = serializers.CharField(source="timeframe.code", read_only=True)
    win_rate = serializers.SerializerMethodField()

    class Meta:
        model = ExpertAdvisor
        fields = [
            "id",
            "user",
            "name",
            "description",
            "version",
            "status",
            "symbol",
            "symbol_name",
            "timeframe",
            "timeframe_code",
            "strategy_type",
            "parameters",
            "risk_per_trade",
            "max_positions",
            "use_stop_loss",
            "use_take_profit",
            "trailing_stop",
            "trailing_stop_pips",
            "total_trades",
            "winning_trades",
            "losing_trades",
            "total_profit",
            "max_drawdown",
            "sharpe_ratio",
            "mql5_code",
            "compiled",
            "ai_generated",
            "backtest_results",
            "created_at",
            "updated_at",
            "deployed_at",
        ]

    def get_win_rate(self, obj):
        if obj.total_trades > 0:
            return round((obj.winning_trades / obj.total_trades) * 100, 2)
        return 0


class EABacktestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = EABacktestResult
        fields = [
            "id",
            "ea",
            "start_date",
            "end_date",
            "initial_balance",
            "final_balance",
            "total_return",
            "max_drawdown",
            "sharpe_ratio",
            "total_trades",
            "winning_trades",
            "losing_trades",
            "profit_factor",
            "equity_curve",
            "trade_history",
            "parameters_used",
            "created_at",
        ]


class EADeploymentSerializer(serializers.ModelSerializer):
    ea_name = serializers.CharField(source="ea.name", read_only=True)

    class Meta:
        model = EADeployment
        fields = ["id", "ea", "ea_name", "mt5_account", "mt5_server", "status", "deployed_at", "stopped_at", "logs"]


class EACreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    symbol = serializers.UUIDField()
    timeframe = serializers.CharField(max_length=5)
    strategy_type = serializers.CharField(max_length=50)
    parameters = serializers.JSONField(default=dict)
    risk_per_trade = serializers.DecimalField(max_digits=5, decimal_places=2, default=2.0)
    use_stop_loss = serializers.BooleanField(default=True)
    use_take_profit = serializers.BooleanField(default=True)


class EAGenerateCodeSerializer(serializers.Serializer):
    ea_id = serializers.UUIDField()
    optimize = serializers.BooleanField(default=False)
