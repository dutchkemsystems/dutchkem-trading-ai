from datetime import timedelta

from django.db.models import Avg, Count, F, Sum
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, Position, Symbol, Trade
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    PositionSerializer,
    SymbolSerializer,
    TradeCreateSerializer,
    TradeSerializer,
)
from .services import OrderExecutionError, RiskCheckError, order_service


class SymbolListView(generics.ListAPIView):
    queryset = Symbol.objects.filter(is_active=True)
    serializer_class = SymbolSerializer
    permission_classes = [permissions.AllowAny]


class SymbolDetailView(generics.RetrieveAPIView):
    queryset = Symbol.objects.all()
    serializer_class = SymbolSerializer
    permission_classes = [permissions.AllowAny]


class TradeListView(generics.ListAPIView):
    serializer_class = TradeSerializer

    def get_queryset(self):
        queryset = Trade.objects.filter(user=self.request.user).select_related(
            "symbol", "timeframe", "signal", "expert_advisor"
        )
        status_filter = self.request.query_params.get("status")
        symbol_filter = self.request.query_params.get("symbol")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if symbol_filter:
            queryset = queryset.filter(symbol__name=symbol_filter)

        return queryset


class TradeDetailView(generics.RetrieveAPIView):
    queryset = Trade.objects.select_related("symbol", "timeframe", "signal", "expert_advisor").all()
    serializer_class = TradeSerializer


class TradeCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TradeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            symbol = Symbol.objects.get(id=serializer.validated_data["symbol"])
        except Symbol.DoesNotExist:
            return Response(
                {"error": "Symbol not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            result = order_service.execute_market_order(
                user=request.user,
                symbol=symbol,
                position_type=serializer.validated_data["position_type"],
                volume=serializer.validated_data["volume"],
                stop_loss=serializer.validated_data.get("stop_loss"),
                take_profit=serializer.validated_data.get("take_profit"),
                signal_id=serializer.validated_data.get("signal_id"),
            )
            return Response(result, status=status.HTTP_201_CREATED)

        except RiskCheckError as e:
            return Response(
                {"error": str(e), "type": "risk_check"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except OrderExecutionError as e:
            return Response(
                {"error": str(e), "type": "execution_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Unexpected error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TradeCloseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, trade_id):
        try:
            result = order_service.close_trade(
                trade_id=str(trade_id),
                user=request.user,
            )
            return Response(result)

        except OrderExecutionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TradeModifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, trade_id):
        try:
            result = order_service.modify_trade(
                trade_id=str(trade_id),
                user=request.user,
                stop_loss=request.data.get("stop_loss"),
                take_profit=request.data.get("take_profit"),
            )
            return Response(result)

        except OrderExecutionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("symbol", "timeframe", "signal")


class OrderCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            symbol = Symbol.objects.get(id=serializer.validated_data["symbol"])
        except Symbol.DoesNotExist:
            return Response(
                {"error": "Symbol not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        valid, message, checks = order_service.validate_order(
            user=request.user,
            symbol=symbol,
            position_type=serializer.validated_data["position_type"],
            volume=serializer.validated_data["volume"],
            stop_loss=serializer.validated_data.get("stop_loss"),
            take_profit=serializer.validated_data.get("take_profit"),
            order_type=serializer.validated_data["order_type"],
        )

        if not valid:
            return Response(
                {"error": message, "checks": checks},
                status=status.HTTP_403_FORBIDDEN,
            )

        from decimal import Decimal

        order = Order.objects.create(
            user=request.user,
            symbol=symbol,
            order_type=serializer.validated_data["order_type"],
            position_type=serializer.validated_data["position_type"],
            volume=serializer.validated_data["volume"],
            price=serializer.validated_data["price"],
            stop_loss=serializer.validated_data.get("stop_loss"),
            take_profit=serializer.validated_data.get("take_profit"),
            expiration=serializer.validated_data.get("expiration"),
            status="PENDING",
        )

        if serializer.validated_data["order_type"] == "MARKET":
            try:
                result = order_service.execute_market_order(
                    user=request.user,
                    symbol=symbol,
                    position_type=serializer.validated_data["position_type"],
                    volume=serializer.validated_data["volume"],
                    stop_loss=serializer.validated_data.get("stop_loss"),
                    take_profit=serializer.validated_data.get("take_profit"),
                )
                order.status = "FILLED"
                order.mt5_ticket = result.get("mt5_ticket")
                order.save()
                return Response(
                    {**OrderSerializer(order).data, "execution": result},
                    status=status.HTTP_201_CREATED,
                )
            except (RiskCheckError, OrderExecutionError) as e:
                order.status = "REJECTED"
                order.save()
                return Response(
                    {"error": str(e), "order": OrderSerializer(order).data},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user, status="PENDING")
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.mt5_ticket:
            import asyncio
            from mcp_integration.services import mt5_service

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(mt5_service.cancel_order(int(order.mt5_ticket)))
            finally:
                loop.close()

        order.status = "CANCELLED"
        order.save()

        return Response(OrderSerializer(order).data)


class PositionListView(generics.ListAPIView):
    serializer_class = PositionSerializer

    def get_queryset(self):
        return Position.objects.filter(user=self.request.user).select_related("symbol", "trade", "timeframe")


class PortfolioSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        positions = Position.objects.filter(user=request.user).select_related("symbol", "trade", "timeframe")

        total_unrealized_pnl = positions.aggregate(total=Sum("unrealized_pnl"))["total"] or 0
        total_margin_used = positions.aggregate(total=Sum("margin_used"))["total"] or 0

        user = request.user

        return Response(
            {
                "balance": user.balance,
                "equity": user.equity,
                "margin_used": total_margin_used,
                "free_margin": user.equity - total_margin_used,
                "unrealized_pnl": total_unrealized_pnl,
                "open_positions": positions.count(),
                "margin_level": (user.equity / total_margin_used * 100) if total_margin_used > 0 else 0,
            }
        )


class TradeHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        trades = Trade.objects.filter(user=request.user, status="CLOSED").select_related(
            "symbol", "signal", "expert_advisor", "timeframe"
        ).order_by("-closed_at")[:100]

        total_profit = trades.aggregate(total=Sum("profit_loss"))["total"] or 0

        winning_trades = trades.filter(profit_loss__gt=0).count()
        losing_trades = trades.filter(profit_loss__lt=0).count()
        total_trades = trades.count()

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        return Response(
            {
                "trades": TradeSerializer(trades, many=True).data,
                "summary": {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": win_rate,
                    "total_profit": total_profit,
                    "average_profit": total_profit / total_trades if total_trades > 0 else 0,
                },
            }
        )
