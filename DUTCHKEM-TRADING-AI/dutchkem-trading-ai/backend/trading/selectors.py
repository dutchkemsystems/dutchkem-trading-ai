from django.db.models import Q
from trading.models import Trade, Position, Order, Symbol


def get_user_trades(user, status=None, symbol=None, timeframe=None, limit=50):
    qs = Trade.objects.select_related("symbol", "timeframe", "signal", "expert_advisor").filter(user=user)
    if status:
        qs = qs.filter(status=status)
    if symbol:
        qs = qs.filter(symbol__name=symbol)
    if timeframe:
        qs = qs.filter(timeframe__code=timeframe)
    return qs.order_by("-opened_at")[:limit]


def get_user_positions(user):
    return (
        Position.objects.select_related("symbol", "trade", "timeframe")
        .filter(user=user, trade__status="OPEN")
        .order_by("-opened_at")
    )


def get_user_orders(user, status=None):
    qs = Order.objects.select_related("symbol", "timeframe").filter(user=user)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")[:50]


def get_user_portfolio(user):
    positions = get_user_positions(user)
    total_unrealized_pnl = sum(float(p.unrealized_pnl) for p in positions)
    total_margin_used = sum(float(p.margin_used) for p in positions)

    return {
        "balance": float(user.balance),
        "equity": float(user.equity),
        "margin": total_margin_used,
        "free_margin": float(user.equity) - total_margin_used,
        "unrealized_pnl": total_unrealized_pnl,
        "open_positions": positions.count(),
    }


def get_active_symbols():
    return Symbol.objects.filter(is_active=True).order_by("category", "name")


def get_symbol_by_name(name: str):
    return Symbol.objects.filter(name=name, is_active=True).first()


def get_trades_by_period(user, start_date, end_date):
    return (
        Trade.objects.select_related("symbol", "timeframe")
        .filter(user=user, status="CLOSED", closed_at__date__gte=start_date, closed_at__date__lte=end_date)
        .order_by("-closed_at")
    )


def get_daily_trade_count(user):
    from django.utils import timezone
    today = timezone.now().date()
    return Trade.objects.filter(user=user, opened_at__date=today).exclude(status="CANCELLED").count()
