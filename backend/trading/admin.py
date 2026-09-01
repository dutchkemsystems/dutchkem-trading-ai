from django.contrib import admin

from .models import Order, Position, Symbol, Trade


@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "description",
        "category",
        "base_currency",
        "quote_currency",
        "pip_size",
        "spread",
        "is_active",
    ]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "description"]
    filter_horizontal = ["supported_timeframes"]


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "symbol",
        "timeframe",
        "position_type",
        "volume",
        "open_price",
        "close_price",
        "status",
        "profit_loss",
        "opened_at",
    ]
    list_filter = ["status", "position_type", "timeframe"]
    search_fields = ["user__username", "symbol__name", "mt5_ticket"]
    date_hierarchy = "opened_at"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "symbol",
        "timeframe",
        "order_type",
        "position_type",
        "volume",
        "price",
        "status",
        "created_at",
    ]
    list_filter = ["status", "order_type", "position_type", "timeframe"]
    search_fields = ["user__username", "symbol__name"]
    date_hierarchy = "created_at"


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "symbol",
        "timeframe",
        "position_type",
        "volume",
        "open_price",
        "current_price",
        "unrealized_pnl",
        "opened_at",
    ]
    list_filter = ["position_type", "timeframe"]
    search_fields = ["user__username", "symbol__name"]
    date_hierarchy = "opened_at"
