# Dutchkem Trading AI — Analytics API Views

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class TradingPerformanceView(APIView):
    """Get comprehensive trading performance metrics"""

    def get(self, request):
        from django.contrib.auth import get_user_model

        from trading.models import Trade

        User = get_user_model()
        user = request.user

        # Time periods
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Get trades for each period
        all_trades = Trade.objects.filter(user=user, status="CLOSED")
        today_trades = all_trades.filter(close_time__date=today)
        week_trades = all_trades.filter(close_time__date__gte=week_ago)
        month_trades = all_trades.filter(close_time__date__gte=month_ago)

        def calculate_metrics(trades):
            if not trades.exists():
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "average_pnl": 0,
                    "best_trade": 0,
                    "worst_trade": 0,
                    "profit_factor": 0,
                    "sharpe_ratio": 0,
                }

            wins = trades.filter(pnl__gt=0)
            losses = trades.filter(pnl__lt=0)

            total_pnl = sum(t.pnl or 0 for t in trades)
            win_pnl = sum(t.pnl or 0 for t in wins)
            loss_pnl = abs(sum(t.pnl or 0 for t in losses))

            return {
                "total_trades": trades.count(),
                "winning_trades": wins.count(),
                "losing_trades": losses.count(),
                "win_rate": round(wins.count() / trades.count() * 100, 2) if trades.count() > 0 else 0,
                "total_pnl": round(float(total_pnl), 2),
                "average_pnl": round(float(total_pnl / trades.count()), 2) if trades.count() > 0 else 0,
                "best_trade": round(float(max((t.pnl or 0) for t in trades)), 2),
                "worst_trade": round(float(min((t.pnl or 0) for t in trades)), 2),
                "profit_factor": round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else 0,
            }

        # PnL by symbol
        symbol_pnl = {}
        for trade in all_trades:
            symbol = trade.symbol.name
            if symbol not in symbol_pnl:
                symbol_pnl[symbol] = {"pnl": 0, "trades": 0, "wins": 0}
            symbol_pnl[symbol]["pnl"] += float(trade.pnl or 0)
            symbol_pnl[symbol]["trades"] += 1
            if trade.pnl and trade.pnl > 0:
                symbol_pnl[symbol]["wins"] += 1

        # PnL by timeframe
        tf_pnl = {}
        for trade in all_trades:
            tf = trade.timeframe or "UNKNOWN"
            if tf not in tf_pnl:
                tf_pnl[tf] = {"pnl": 0, "trades": 0, "wins": 0}
            tf_pnl[tf]["pnl"] += float(trade.pnl or 0)
            tf_pnl[tf]["trades"] += 1
            if trade.pnl and trade.pnl > 0:
                tf_pnl[tf]["wins"] += 1

        # Daily PnL for chart
        daily_pnl = []
        for i in range(30):
            date = today - timedelta(days=i)
            day_trades = all_trades.filter(close_time__date=date)
            day_pnl = sum(float(t.pnl or 0) for t in day_trades)
            daily_pnl.append({"date": date.isoformat(), "pnl": round(day_pnl, 2)})
        daily_pnl.reverse()

        return Response(
            {
                "today": calculate_metrics(today_trades),
                "week": calculate_metrics(week_trades),
                "month": calculate_metrics(month_trades),
                "all_time": calculate_metrics(all_trades),
                "symbol_breakdown": symbol_pnl,
                "timeframe_breakdown": tf_pnl,
                "daily_pnl": daily_pnl,
            }
        )


class RiskAnalyticsView(APIView):
    """Get risk analytics and metrics"""

    def get(self, request):
        from risk_management.models import DrawdownMonitor, RiskAlert, RiskParameter

        user = request.user

        # Get risk parameters
        risk_params = RiskParameter.objects.filter(is_active=True).first()
        drawdown = DrawdownMonitor.objects.filter(user=user).first()

        # Get recent alerts
        recent_alerts = RiskAlert.objects.filter(
            user=user, created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by("-created_at")[:10]

        return Response(
            {
                "risk_parameters": {
                    "max_daily_loss": float(risk_params.max_daily_loss) if risk_params else 2.0,
                    "daily_growth_target": float(risk_params.daily_growth_target) if risk_params else 0.14,
                    "max_drawdown": float(risk_params.max_drawdown) if risk_params else 15.0,
                    "max_daily_trades": risk_params.max_daily_trades if risk_params else 10,
                },
                "current_status": {
                    "daily_pnl_percent": float(drawdown.daily_pnl_percent) if drawdown else 0,
                    "drawdown_percent": float(drawdown.drawdown_percent) if drawdown else 0,
                    "daily_trades_count": drawdown.daily_trades_count if drawdown else 0,
                    "daily_loss_remaining": (
                        float(risk_params.max_daily_loss - abs(drawdown.daily_pnl_percent))
                        if risk_params and drawdown
                        else 2.0
                    ),
                    "drawdown_remaining": (
                        float(risk_params.max_drawdown - drawdown.drawdown_percent)
                        if risk_params and drawdown
                        else 15.0
                    ),
                },
                "circuit_breakers": {
                    "daily_loss_active": (
                        abs(drawdown.daily_pnl_percent) >= risk_params.max_daily_loss
                        if drawdown and risk_params
                        else False
                    ),
                    "max_drawdown_active": (
                        drawdown.drawdown_percent >= risk_params.max_drawdown if drawdown and risk_params else False
                    ),
                    "daily_trades_active": (
                        drawdown.daily_trades_count >= risk_params.max_daily_trades
                        if drawdown and risk_params
                        else False
                    ),
                },
                "recent_alerts": [
                    {
                        "type": alert.alert_type,
                        "severity": alert.severity,
                        "message": alert.message,
                        "created_at": alert.created_at.isoformat(),
                    }
                    for alert in recent_alerts
                ],
            }
        )


class SignalAnalyticsView(APIView):
    """Get signal analytics and performance"""

    def get(self, request):
        from signals.models import Signal
        from trading.models import Symbol

        user = request.user

        # Get all signals
        all_signals = Signal.objects.all()
        active_signals = all_signals.filter(status="ACTIVE")
        recent_signals = all_signals.order_by("-created_at")[:50]

        # Signal performance by timeframe
        tf_performance = {}
        for tf in ["M5", "M15", "M30", "H1", "H2", "H4"]:
            tf_signals = all_signals.filter(timeframe__code=tf)
            if tf_signals.exists():
                avg_strength = sum(float(s.strength or 0) for s in tf_signals) / tf_signals.count()
                tf_performance[tf] = {
                    "total": tf_signals.count(),
                    "active": tf_signals.filter(status="ACTIVE").count(),
                    "average_strength": round(avg_strength, 2),
                }

        # Signal direction distribution
        buy_signals = all_signals.filter(signal_type="BUY").count()
        sell_signals = all_signals.filter(signal_type="SELL").count()

        return Response(
            {
                "summary": {
                    "total_signals": all_signals.count(),
                    "active_signals": active_signals.count(),
                    "buy_signals": buy_signals,
                    "sell_signals": sell_signals,
                },
                "timeframe_performance": tf_performance,
                "recent_signals": [
                    {
                        "id": str(s.id),
                        "symbol": s.symbol.name,
                        "type": s.signal_type,
                        "strength": float(s.strength) if s.strength else 0,
                        "timeframe": s.timeframe.code if s.timeframe else "N/A",
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in recent_signals
                ],
            }
        )
