from rest_framework import serializers

from .models import Order, Position, Symbol, Trade


class SymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symbol
        fields = [
            "id",
            "name",
            "description",
            "category",
            "base_currency",
            "quote_currency",
            "pip_size",
            "spread",
            "contract_size",
            "margin_requirement",
            "is_active",
        ]


class TradeSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)
    duration = serializers.DurationField(read_only=True)

    class Meta:
        model = Trade
        fields = [
            "id",
            "symbol",
            "symbol_name",
            "position_type",
            "volume",
            "open_price",
            "close_price",
            "stop_loss",
            "take_profit",
            "status",
            "profit_loss",
            "commission",
            "swap",
            "mt5_ticket",
            "signal",
            "expert_advisor",
            "opened_at",
            "closed_at",
            "duration",
        ]
        read_only_fields = ["id", "status", "profit_loss", "commission", "swap", "opened_at", "closed_at"]


class OrderSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "symbol",
            "symbol_name",
            "order_type",
            "position_type",
            "volume",
            "price",
            "stop_loss",
            "take_profit",
            "status",
            "risk_amount",
            "risk_reward_ratio",
            "mt5_ticket",
            "signal",
            "expiration",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class PositionSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)

    class Meta:
        model = Position
        fields = [
            "id",
            "symbol",
            "symbol_name",
            "position_type",
            "volume",
            "open_price",
            "current_price",
            "stop_loss",
            "take_profit",
            "unrealized_pnl",
            "margin_used",
            "opened_at",
            "updated_at",
        ]


class TradeCreateSerializer(serializers.Serializer):
    symbol = serializers.UUIDField()
    position_type = serializers.ChoiceField(choices=["BUY", "SELL"])
    volume = serializers.DecimalField(max_digits=10, decimal_places=2)
    stop_loss = serializers.DecimalField(max_digits=20, decimal_places=6, required=False)
    take_profit = serializers.DecimalField(max_digits=20, decimal_places=6, required=False)
    signal_id = serializers.UUIDField(required=False)


class OrderCreateSerializer(serializers.Serializer):
    symbol = serializers.UUIDField()
    order_type = serializers.ChoiceField(choices=["MARKET", "LIMIT", "STOP", "STOP_LIMIT"])
    position_type = serializers.ChoiceField(choices=["BUY", "SELL"])
    volume = serializers.DecimalField(max_digits=10, decimal_places=2)
    price = serializers.DecimalField(max_digits=20, decimal_places=6)
    stop_loss = serializers.DecimalField(max_digits=20, decimal_places=6, required=False)
    take_profit = serializers.DecimalField(max_digits=20, decimal_places=6, required=False)
    expiration = serializers.DateTimeField(required=False)
