from django.db.models import Avg
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Indicator,
    IndicatorCategory,
    IndicatorValue,
    Timeframe,
    TimeframeIndicatorConfig,
)
from .serializers import (
    IndicatorCategorySerializer,
    IndicatorSerializer,
    IndicatorValueSerializer,
    TimeframeIndicatorConfigSerializer,
    TimeframeSerializer,
)


class TimeframeListView(generics.ListAPIView):
    queryset = Timeframe.objects.filter(is_active=True)
    serializer_class = TimeframeSerializer
    permission_classes = [permissions.AllowAny]


class TimeframeDetailView(generics.RetrieveAPIView):
    queryset = Timeframe.objects.all()
    serializer_class = TimeframeSerializer
    permission_classes = [permissions.AllowAny]


class IndicatorCategoryListView(generics.ListAPIView):
    queryset = IndicatorCategory.objects.all()
    serializer_class = IndicatorCategorySerializer
    permission_classes = [permissions.AllowAny]


class IndicatorListView(generics.ListAPIView):
    serializer_class = IndicatorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Indicator.objects.filter(is_active=True)
        category = self.request.query_params.get("category")
        indicator_type = self.request.query_params.get("type")
        timeframe = self.request.query_params.get("timeframe")

        if category:
            queryset = queryset.filter(category__name=category)
        if indicator_type:
            queryset = queryset.filter(indicator_type=indicator_type)
        if timeframe:
            queryset = queryset.filter(suitable_timeframes__code=timeframe)

        return queryset.distinct()


class IndicatorDetailView(generics.RetrieveAPIView):
    queryset = Indicator.objects.all()
    serializer_class = IndicatorSerializer
    permission_classes = [permissions.AllowAny]


class IndicatorValueListView(generics.ListAPIView):
    serializer_class = IndicatorValueSerializer

    def get_queryset(self):
        queryset = IndicatorValue.objects.all()
        symbol = self.request.query_params.get("symbol")
        indicator = self.request.query_params.get("indicator")
        timeframe = self.request.query_params.get("timeframe")

        if symbol:
            queryset = queryset.filter(symbol__name=symbol)
        if indicator:
            queryset = queryset.filter(indicator__name=indicator)
        if timeframe:
            queryset = queryset.filter(timeframe__code=timeframe)

        return queryset[:100]


class TimeframeIndicatorConfigView(generics.ListAPIView):
    serializer_class = TimeframeIndicatorConfigSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        timeframe = self.request.query_params.get("timeframe")
        if timeframe:
            return TimeframeIndicatorConfig.objects.filter(timeframe__code=timeframe)
        return TimeframeIndicatorConfig.objects.all()


class IndicatorCalculationView(APIView):
    """Trigger indicator calculation for a symbol and timeframe"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        import logging
        from config.tasks import calculate_indicators

        logger = logging.getLogger("indicators")

        symbol_id = request.data.get("symbol")
        timeframe_code = request.data.get("timeframe")

        if not symbol_id or not timeframe_code:
            return Response(
                {"error": "Both 'symbol' and 'timeframe' are required."},
                status=400,
            )

        # Queue real Celery task to calculate indicators
        task = calculate_indicators.delay(str(symbol_id), str(timeframe_code))

        return Response({
            "status": "calculation_queued",
            "task_id": task.id,
            "symbol": symbol_id,
            "timeframe": timeframe_code,
        })
