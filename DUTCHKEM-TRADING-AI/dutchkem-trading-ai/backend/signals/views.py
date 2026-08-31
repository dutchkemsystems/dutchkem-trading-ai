from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConfluenceScore, Signal, SignalHistory
from .serializers import (
    ConfluenceScoreSerializer,
    SignalGenerateSerializer,
    SignalHistorySerializer,
    SignalSerializer,
)


class SignalListView(generics.ListAPIView):
    serializer_class = SignalSerializer

    def get_queryset(self):
        queryset = Signal.objects.filter(is_active=True)
        symbol = self.request.query_params.get("symbol")
        timeframe = self.request.query_params.get("timeframe")
        signal_type = self.request.query_params.get("type")

        if symbol:
            queryset = queryset.filter(symbol__name=symbol)
        if timeframe:
            queryset = queryset.filter(timeframe__code=timeframe)
        if signal_type:
            queryset = queryset.filter(signal_type=signal_type)

        return queryset


class SignalDetailView(generics.RetrieveAPIView):
    queryset = Signal.objects.all()
    serializer_class = SignalSerializer


class SignalHistoryView(generics.ListAPIView):
    serializer_class = SignalHistorySerializer

    def get_queryset(self):
        # Signal model has no user FK — return recent history for active symbols
        qs = SignalHistory.objects.select_related("signal", "signal__symbol", "signal__timeframe")
        return qs.order_by("-closed_at")[:100]


class ConfluenceScoreListView(generics.ListAPIView):
    serializer_class = ConfluenceScoreSerializer

    def get_queryset(self):
        queryset = ConfluenceScore.objects.all()
        symbol = self.request.query_params.get("symbol")
        if symbol:
            queryset = queryset.filter(symbol__name=symbol)
        return queryset


class SignalGenerateView(APIView):
    """Generate signals using AI multi-agent system"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        import logging
        from strategies.confluence import confluence_engine
        from trading.models import Symbol
        from indicators.models import Timeframe

        logger = logging.getLogger("signals")

        serializer = SignalGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        symbol_name = serializer.validated_data.get("symbol", "EURUSD")
        timeframe_code = serializer.validated_data.get("timeframe", "H1")

        # Get symbols to generate signals for
        symbols = Symbol.objects.filter(is_active=True)
        if symbol_name:
            symbols = symbols.filter(name=symbol_name)

        # Resolve the default timeframe FK for new signals
        try:
            default_timeframe = Timeframe.objects.get(code=timeframe_code)
        except Timeframe.DoesNotExist:
            default_timeframe = Timeframe.objects.filter(is_active=True).first()

        signals_created = []
        for symbol in symbols:
            try:
                # Use confluence engine to generate signal
                result = confluence_engine.analyze_symbol(symbol.name)
                if result and result.get("should_trade"):
                    signal = Signal.objects.create(
                        symbol=symbol,
                        timeframe=default_timeframe,
                        signal_type=result.get("direction", "NEUTRAL"),
                        strength=result.get("total_score", 0),
                        confluence_score=result.get("total_score", 0),
                        generated_by="api_request",
                    )
                    signals_created.append(str(signal.id))
            except Exception as exc:
                logger.error("Signal generation failed for %s: %s", symbol.name, exc)

        return Response({
            "status": "success",
            "signals_created": len(signals_created),
            "signal_ids": signals_created,
        })


class ActiveSignalsView(APIView):
    """Get all active signals for the user"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        signals = Signal.objects.filter(is_active=True).order_by("-strength")[:20]
        return Response(SignalSerializer(signals, many=True).data)
