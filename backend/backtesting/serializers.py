from rest_framework import serializers

from .models import BacktestResult


class BacktestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestResult
        fields = "__all__"
        read_only_fields = [
            "id", "user", "created_at", "final_balance", "total_pnl",
            "total_pnl_percent", "total_trades", "winning_trades", "losing_trades",
            "win_rate", "profit_factor", "max_drawdown", "sharpe_ratio", "trades", "equity_curve",
        ]
