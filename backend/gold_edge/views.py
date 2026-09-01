import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GoldEdgeBacktest, GoldEdgeConfig, GoldEdgeSignal
from .serializers import (
    GoldEdgeAnalysisRequestSerializer,
    GoldEdgeBacktestSerializer,
    GoldEdgeConfigSerializer,
    GoldEdgeScanRequestSerializer,
    GoldEdgeSignalSerializer,
)
from .services import gold_edge_service

logger = logging.getLogger("gold_edge.views")


# ------------------------------------------------------------------
# Config CRUD
# ------------------------------------------------------------------

class GoldEdgeConfigListView(generics.ListCreateAPIView):
    serializer_class = GoldEdgeConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = GoldEdgeConfig.objects.filter(is_active=True)
        symbol = self.request.query_params.get("symbol")
        if symbol:
            qs = qs.filter(symbol__name=symbol)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoldEdgeConfigDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GoldEdgeConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GoldEdgeConfig.objects.filter(user=self.request.user)


# ------------------------------------------------------------------
# Signals
# ------------------------------------------------------------------

class GoldEdgeSignalListView(generics.ListAPIView):
    serializer_class = GoldEdgeSignalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = GoldEdgeSignal.objects.select_related("symbol", "timeframe", "config")
        symbol = self.request.query_params.get("symbol")
        direction = self.request.query_params.get("direction")
        active_only = self.request.query_params.get("active")

        if symbol:
            qs = qs.filter(symbol__name=symbol)
        if direction:
            qs = qs.filter(direction=direction.upper())
        if active_only == "1":
            qs = qs.filter(is_active=True)

        return qs[:200]


class GoldEdgeSignalDetailView(generics.RetrieveAPIView):
    serializer_class = GoldEdgeSignalSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = GoldEdgeSignal.objects.all()


# ------------------------------------------------------------------
# On-demand analysis
# ------------------------------------------------------------------

class GoldEdgeAnalysisView(APIView):
    """
    Run the full Gold Edge pipeline on-demand for a symbol/timeframe.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = GoldEdgeAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        symbol = serializer.validated_data["symbol"]
        timeframe = serializer.validated_data.get("timeframe", "H1")
        config_id = serializer.validated_data.get("config_id")

        # Load config overrides if provided
        config_overrides = None
        if config_id:
            try:
                cfg = GoldEdgeConfig.objects.get(id=config_id)
                config_overrides = {
                    "momentum_weight": float(cfg.momentum_weight),
                    "trend_weight": float(cfg.trend_weight),
                    "volatility_weight": float(cfg.volatility_weight),
                    "dxy_correlation_weight": float(cfg.dxy_correlation_weight),
                    "atr_period": cfg.atr_period,
                    "ema_period": cfg.ema_period,
                    "atr_multipliers": cfg.atr_multipliers,
                    "atr_ratio_min": float(cfg.atr_ratio_min),
                    "atr_ratio_max": float(cfg.atr_ratio_max),
                    "min_gec_score": float(cfg.min_gec_score),
                    "min_combined_score": float(cfg.min_combined_score),
                    "sl_atr_multiplier": float(cfg.sl_atr_multiplier),
                    "tp_atr_multiplier": float(cfg.tp_atr_multiplier),
                }
            except GoldEdgeConfig.DoesNotExist:
                pass

        result = gold_edge_service.run_pipeline(symbol, timeframe, config_overrides)

        # Auto-store if there is an actionable signal
        signal_id = None
        if result.action in ("ENTRY", "WATCH") and config_id:
            signal_id = gold_edge_service.store_signal(
                str(config_id), symbol, timeframe, result
            )

        response_data = result.to_dict()
        response_data["symbol"] = symbol
        response_data["timeframe"] = timeframe
        response_data["signal_id"] = signal_id

        return Response(response_data)


# ------------------------------------------------------------------
# Batch scanner
# ------------------------------------------------------------------

class GoldEdgeScanView(APIView):
    """
    Scan multiple symbols for Gold Edge setups.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = GoldEdgeScanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        symbols = serializer.validated_data["symbols"]
        timeframe = serializer.validated_data.get("timeframe", "H1")
        config_id = serializer.validated_data.get("config_id")

        config_overrides = None
        if config_id:
            try:
                cfg = GoldEdgeConfig.objects.get(id=config_id)
                config_overrides = {
                    "momentum_weight": float(cfg.momentum_weight),
                    "trend_weight": float(cfg.trend_weight),
                    "volatility_weight": float(cfg.volatility_weight),
                    "dxy_correlation_weight": float(cfg.dxy_correlation_weight),
                    "atr_period": cfg.atr_period,
                    "ema_period": cfg.ema_period,
                    "atr_multipliers": cfg.atr_multipliers,
                    "atr_ratio_min": float(cfg.atr_ratio_min),
                    "atr_ratio_max": float(cfg.atr_ratio_max),
                    "min_gec_score": float(cfg.min_gec_score),
                    "min_combined_score": float(cfg.min_combined_score),
                    "sl_atr_multiplier": float(cfg.sl_atr_multiplier),
                    "tp_atr_multiplier": float(cfg.tp_atr_multiplier),
                }
            except GoldEdgeConfig.DoesNotExist:
                pass

        results = gold_edge_service.scan_symbols(symbols, timeframe, config_overrides)

        return Response({
            "status": "success",
            "timeframe": timeframe,
            "signals_found": len(results),
            "results": results,
        })


# ------------------------------------------------------------------
# Backtesting
# ------------------------------------------------------------------

class GoldEdgeBacktestListView(generics.ListCreateAPIView):
    serializer_class = GoldEdgeBacktestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GoldEdgeBacktest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        bt = serializer.save(user=self.request.user, status="PENDING")
        # Queue the backtest task
        try:
            from config.tasks import run_gold_edge_backtest
            run_gold_edge_backtest.delay(str(bt.id))
        except Exception as exc:
            logger.error("Failed to queue Gold Edge backtest: %s", exc)
            bt.status = "FAILED"
            bt.save()


class GoldEdgeBacktestDetailView(generics.RetrieveAPIView):
    serializer_class = GoldEdgeBacktestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GoldEdgeBacktest.objects.filter(user=self.request.user)
