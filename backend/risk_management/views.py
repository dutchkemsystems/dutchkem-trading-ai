from datetime import date

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CorrelationMatrix,
    DailyPerformance,
    DrawdownMonitor,
    PositionSizing,
    RiskAlert,
    RiskParameter,
)
from .serializers import (
    CorrelationMatrixSerializer,
    DrawdownMonitorSerializer,
    PositionSizeCalculateSerializer,
    PositionSizingSerializer,
    RiskAlertSerializer,
    RiskParameterSerializer,
)


class RiskParameterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        params = RiskParameter.objects.filter(is_active=True).first()
        if params:
            return Response(RiskParameterSerializer(params).data)
        return Response({})


class PositionSizingView(APIView):
    """
    Calculate position size based on daily risk budget

    Daily Risk Budget:
    - Risk per trade: 1% of equity
    - Daily loss limit: 2% of equity
    - Max daily trades: 10
    - Adjusts based on remaining daily budget
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PositionSizeCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from trading.models import Symbol

        symbol = Symbol.objects.get(id=serializer.validated_data["symbol"])
        risk_params = RiskParameter.objects.filter(is_active=True).first()

        equity = request.user.equity
        risk_per = float(serializer.validated_data.get("risk_per_trade", 1.0))  # Default 1% now
        sl_pips = serializer.validated_data["stop_loss_pips"]

        # Get daily trading status
        monitor = DrawdownMonitor.objects.filter(user=request.user).first()
        daily_pnl = monitor.daily_pnl if monitor else 0
        daily_trades = monitor.daily_trades_count if monitor else 0

        # Calculate remaining daily budget
        daily_loss_limit = float(equity) * 0.02  # 2% daily loss limit
        remaining_budget = daily_loss_limit + float(daily_pnl)

        # Calculate risk amount (1% of equity per trade, but capped by remaining budget)
        risk_amount = float(equity) * (risk_per / 100)
        if risk_amount > remaining_budget:
            risk_amount = remaining_budget

        # Calculate position size
        position_size = risk_amount / sl_pips if sl_pips > 0 else 0

        result = PositionSizing.objects.create(
            user=request.user,
            symbol=symbol,
            timeframe=serializer.validated_data.get("timeframe"),
            risk_per_trade=risk_per,
            account_equity=equity,
            risk_amount=risk_amount,
            stop_loss_pips=sl_pips,
            position_size=round(position_size, 2),
            daily_pnl=daily_pnl,
            daily_trades_count=daily_trades,
            remaining_daily_budget=remaining_budget,
        )

        return Response(PositionSizingSerializer(result).data)


class DrawdownMonitorView(generics.ListAPIView):
    serializer_class = DrawdownMonitorSerializer

    def get_queryset(self):
        return DrawdownMonitor.objects.filter(user=self.request.user)


class DrawdownStatusView(APIView):
    """
    Get current drawdown and daily risk status

    Circuit Breakers:
    - Daily loss limit: 2% of equity
    - Max drawdown: 15% of equity
    - Daily target lock: Trading stops at 0.4% daily gain
    - Max daily trades: 10
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        monitor = DrawdownMonitor.objects.filter(user=request.user).first()
        risk_params = RiskParameter.objects.filter(is_active=True).first()

        if not monitor:
            return Response(
                {
                    "drawdown_percent": 0,
                    "daily_pnl": 0,
                    "daily_pnl_percent": 0,
                    "daily_loss_percent": 0,
                    "daily_trades_count": 0,
                    "is_circuit_breaker_triggered": False,
                    "is_daily_loss_triggered": False,
                    "is_drawdown_triggered": False,
                    "is_daily_target_triggered": False,
                    "is_max_trades_triggered": False,
                    "max_drawdown_limit": risk_params.max_drawdown if risk_params else 15,
                    "max_daily_loss_limit": risk_params.max_daily_loss if risk_params else 2,
                    "daily_target_lock": risk_params.daily_target_lock if risk_params else 0.4,
                    "max_daily_trades": risk_params.max_daily_trades if risk_params else 10,
                }
            )

        return Response(monitor.get_status())


class RiskAlertListView(generics.ListAPIView):
    serializer_class = RiskAlertSerializer

    def get_queryset(self):
        return RiskAlert.objects.filter(user=self.request.user)


class RiskDashboardView(APIView):
    """
    Comprehensive risk dashboard with daily performance metrics
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        monitor = DrawdownMonitor.objects.filter(user=request.user).first()
        risk_params = RiskParameter.objects.filter(is_active=True).first()
        alerts = RiskAlert.objects.filter(user=request.user, is_read=False)

        # Get today's performance
        today_performance = DailyPerformance.objects.filter(user=request.user, date=date.today()).first()

        return Response(
            {
                "drawdown": monitor.get_status() if monitor else None,
                "risk_params": RiskParameterSerializer(risk_params).data if risk_params else None,
                "daily_performance": {
                    "date": date.today().isoformat(),
                    "starting_equity": (
                        str(today_performance.starting_equity) if today_performance else str(request.user.equity)
                    ),
                    "current_equity": str(request.user.equity),
                    "daily_pnl": str(today_performance.daily_pnl) if today_performance else "0",
                    "daily_pnl_percent": str(today_performance.daily_pnl_percent) if today_performance else "0",
                    "total_trades": today_performance.total_trades if today_performance else 0,
                    "win_rate": str(today_performance.win_rate) if today_performance else "0",
                    "risk_reward_ratio": str(today_performance.risk_reward_ratio) if today_performance else "0",
                },
                "unread_alerts": alerts.count(),
                "recent_alerts": RiskAlertSerializer(alerts[:5], many=True).data,
                "trading_status": (
                    monitor.get_status()
                    if monitor
                    else {"is_circuit_breaker_triggered": False, "daily_trades_count": 0, "daily_pnl_percent": 0}
                ),
            }
        )


class DailyPerformanceView(APIView):
    """
    Get daily performance history
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        performances = DailyPerformance.objects.filter(user=request.user).order_by("-date")[:days]

        return Response(
            {
                "performances": [
                    {
                        "date": p.date.isoformat(),
                        "daily_pnl": str(p.daily_pnl),
                        "daily_pnl_percent": str(p.daily_pnl_percent),
                        "total_trades": p.total_trades,
                        "win_rate": str(p.win_rate),
                        "risk_reward_ratio": str(p.risk_reward_ratio),
                        "timeframe_performance": p.timeframe_performance,
                    }
                    for p in performances
                ],
                "summary": {
                    "total_days": performances.count(),
                    "profitable_days": performances.filter(daily_pnl__gt=0).count(),
                    "losing_days": performances.filter(daily_pnl__lt=0).count(),
                    "avg_daily_pnl": str(performances.aggregate(avg=Avg("daily_pnl_percent"))["avg"] or 0),
                    "total_pnl": str(performances.aggregate(total=Sum("daily_pnl"))["total"] or 0),
                },
            }
        )


class DailyTargetView(APIView):
    """
    Get daily target status and enforce target lock.
    Three profiles: conservative (0.80%), moderate (1.45%), aggressive (2.20%)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .daily_target import DailyTargetLock

        profile = request.query_params.get("profile", "moderate")
        lock = DailyTargetLock(profile=profile)
        status = lock.check_daily_status(request.user)
        return Response(status)

    def post(self, request):
        from .daily_target import DailyTargetLock

        profile = request.data.get("profile", "moderate")
        lock = DailyTargetLock(profile=profile)
        result = lock.enforce_daily_target(request.user)
        return Response(result)


class DailyTargetOverrideView(APIView):
    """
    Override daily target halt for emergency situations.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .daily_target import DailyTargetLock

        reason = request.data.get("reason", "manual_override")
        lock = DailyTargetLock()
        result = lock.override_halt(request.user, reason=reason)
        return Response(result)
