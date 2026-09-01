import asyncio

from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MCPConnection, MCPServer, MCPTool
from .serializers import (
    MCPCallSerializer,
    MCPConnectionSerializer,
    MCPServerSerializer,
    MCPToolSerializer,
)
from .services import mt5_service


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class MCPServerListView(generics.ListAPIView):
    queryset = MCPServer.objects.filter(is_active=True)
    serializer_class = MCPServerSerializer
    permission_classes = [permissions.AllowAny]


class MCPServerDetailView(generics.RetrieveAPIView):
    queryset = MCPServer.objects.all()
    serializer_class = MCPServerSerializer


class MCPToolListView(generics.ListAPIView):
    serializer_class = MCPToolSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = MCPTool.objects.filter(is_active=True)
        server = self.request.query_params.get("server")
        if server:
            queryset = queryset.filter(server__name=server)
        return queryset


class MCPConnectionListView(generics.ListAPIView):
    serializer_class = MCPConnectionSerializer

    def get_queryset(self):
        return MCPConnection.objects.all()[:20]


class MCPCallView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MCPCallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tool_name = serializer.validated_data["tool"]
        parameters = serializer.validated_data.get("parameters", {})

        tool_map = {
            "get_account_info": lambda: run_async(mt5_service.get_account_info()),
            "get_positions": lambda: run_async(mt5_service.get_positions()),
            "get_orders": lambda: run_async(mt5_service.get_orders()),
            "get_symbols": lambda: run_async(mt5_service.get_symbols()),
            "get_symbol_info": lambda: run_async(mt5_service.get_symbol_info(
                parameters.get("symbol", "")
            )),
            "get_candles": lambda: run_async(mt5_service.get_candles(
                parameters.get("symbol", ""),
                parameters.get("timeframe", "H1"),
                parameters.get("count", 100),
            )),
            "get_tick_data": lambda: run_async(mt5_service.get_tick_data(
                parameters.get("symbol", "")
            )),
            "get_trade_history": lambda: run_async(mt5_service.get_trade_history(
                parameters.get("days", 30)
            )),
            "get_performance_stats": lambda: run_async(mt5_service.get_performance_stats()),
            "open_position": lambda: run_async(mt5_service.open_position(
                symbol=parameters.get("symbol", ""),
                volume=parameters.get("volume", 0.01),
                position_type=parameters.get("type", "BUY"),
                stop_loss=parameters.get("sl", 0.0),
                take_profit=parameters.get("tp", 0.0),
                magic=parameters.get("magic", 123456),
            )),
            "close_position": lambda: run_async(mt5_service.close_position(
                parameters.get("ticket", 0)
            )),
            "modify_position": lambda: run_async(mt5_service.modify_position(
                parameters.get("ticket", 0),
                parameters.get("sl", 0.0),
                parameters.get("tp", 0.0),
            )),
            "place_order": lambda: run_async(mt5_service.place_pending_order(
                symbol=parameters.get("symbol", ""),
                volume=parameters.get("volume", 0.01),
                order_type=parameters.get("order_type", "LIMIT"),
                position_type=parameters.get("type", "BUY"),
                price=parameters.get("price", 0.0),
                stop_loss=parameters.get("sl", 0.0),
                take_profit=parameters.get("tp", 0.0),
            )),
            "cancel_order": lambda: run_async(mt5_service.cancel_order(
                parameters.get("ticket", 0)
            )),
        }

        handler = tool_map.get(tool_name)
        if handler is None:
            return Response(
                {"status": "error", "message": f"Unknown tool: {tool_name}"},
                status=400,
            )

        try:
            result = handler()
            return Response({
                "status": "success",
                "tool": tool_name,
                "result": result,
            })
        except Exception as e:
            return Response(
                {"status": "error", "tool": tool_name, "message": str(e)},
                status=500,
            )


class MCPHealthCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        health = run_async(mt5_service.health_check())
        return Response(health)


class MT5ConnectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        result = run_async(mt5_service.connect())
        if result.get("success"):
            server, _ = MCPServer.objects.get_or_create(
                name="SYNX-MT5",
                defaults={
                    "display_name": "SYNX-MT5-MCP",
                    "description": "MetaTrader 5 integration",
                    "endpoint_url": mt5_service.config.base_url,
                    "is_active": True,
                },
            )
            MCPConnection.objects.create(
                server=server,
                session_id=f"django-{timezone.now().timestamp()}",
                status="CONNECTED",
            )
        return Response(result)


class MT5DisconnectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        result = run_async(mt5_service.disconnect())
        return Response(result)


class MT5StatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "connected": mt5_service.is_connected,
            "stats": mt5_service.stats,
            "config": {
                "host": mt5_service.config.host,
                "http_port": mt5_service.config.http_port,
                "ws_port": mt5_service.config.ws_port,
            },
        })


class MT5SymbolsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        result = run_async(mt5_service.get_symbols())
        return Response(result)


class MT5AccountInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        result = run_async(mt5_service.get_account_info())
        return Response(result)


class MT5PositionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        positions = run_async(mt5_service.get_positions())
        return Response({"positions": positions})


class MT5OrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = run_async(mt5_service.get_orders())
        return Response({"orders": orders})


class MT5CandlesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        symbol = request.query_params.get("symbol", "EURUSD")
        timeframe = request.query_params.get("timeframe", "H1")
        count = int(request.query_params.get("count", 100))
        candles = run_async(mt5_service.get_candles(symbol, timeframe, count))
        return Response({"candles": candles})


class MT5OpenPositionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        result = run_async(mt5_service.open_position(
            symbol=request.data.get("symbol", ""),
            volume=float(request.data.get("volume", 0.01)),
            position_type=request.data.get("position_type", "BUY"),
            stop_loss=float(request.data.get("stop_loss", 0)),
            take_profit=float(request.data.get("take_profit", 0)),
            magic=int(request.data.get("magic", 123456)),
        ))
        return Response(result)


class MT5ClosePositionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ticket = request.data.get("ticket")
        if not ticket:
            return Response({"error": "ticket required"}, status=400)
        result = run_async(mt5_service.close_position(int(ticket)))
        return Response(result)


class MT5ModifyPositionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ticket = request.data.get("ticket")
        if not ticket:
            return Response({"error": "ticket required"}, status=400)
        result = run_async(mt5_service.modify_position(
            int(ticket),
            float(request.data.get("stop_loss", 0)),
            float(request.data.get("take_profit", 0)),
        ))
        return Response(result)


class MT5TradeHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        trades = run_async(mt5_service.get_trade_history(days))
        return Response({"trades": trades})
