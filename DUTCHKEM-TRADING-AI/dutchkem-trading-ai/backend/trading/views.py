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
        queryset = Trade.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get("status")
        symbol_filter = self.request.query_params.get("symbol")

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if symbol_filter:
            queryset = queryset.filter(symbol__name=symbol_filter)

        return queryset


class TradeDetailView(generics.RetrieveAPIView):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer


class TradeCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TradeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Here we would integrate with MT5 via SYNX-MT5-MCP
        # For now, create the trade record
        symbol = Symbol.objects.get(id=serializer.validated_data["symbol"])

        trade = Trade.objects.create(
            user=request.user,
            symbol=symbol,
            position_type=serializer.validated_data["position_type"],
            volume=serializer.validated_data["volume"],
            open_price=0,  # Would be filled from MT5
            stop_loss=serializer.validated_data.get("stop_loss"),
            take_profit=serializer.validated_data.get("take_profit"),
            status="PENDING",
        )

        return Response(TradeSerializer(trade).data, status=status.HTTP_201_CREATED)


class TradeCloseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, trade_id):
        try:
            trade = Trade.objects.get(id=trade_id, user=request.user, status="OPEN")
        except Trade.DoesNotExist:
            return Response({"error": "Trade not found"}, status=status.HTTP_404_NOT_FOUND)

        # Close trade via MT5
        trade.status = "CLOSED"
        trade.closed_at = timezone.now()
        trade.save()

        return Response(TradeSerializer(trade).data)


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        symbol = Symbol.objects.get(id=serializer.validated_data["symbol"])

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

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user, status="PENDING")
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        order.status = "CANCELLED"
        order.save()

        return Response(OrderSerializer(order).data)


class PositionListView(generics.ListAPIView):
    serializer_class = PositionSerializer

    def get_queryset(self):
        return Position.objects.filter(user=self.request.user)


class PortfolioSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        positions = Position.objects.filter(user=request.user)

        total_unrealized_pnl = positions.aggregate(total=Sum("unrealized_pnl"))["total"] or 0

        total_margin_used = positions.aggregate(total=Sum("margin_used"))["total"] or 0

        # Get user's account info
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
        trades = Trade.objects.filter(user=request.user, status="CLOSED").order_by("-closed_at")[:100]

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
