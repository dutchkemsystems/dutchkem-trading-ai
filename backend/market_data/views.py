from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EconomicCalendar, LivePrice, MarketData, MarketSentiment
from .serializers import (
    EconomicCalendarSerializer,
    LivePriceSerializer,
    MarketDataSerializer,
    MarketSentimentSerializer,
)


class MarketDataListView(generics.ListAPIView):
    serializer_class = MarketDataSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = MarketData.objects.all()
        symbol = self.request.query_params.get("symbol")
        timeframe = self.request.query_params.get("timeframe")
        limit = self.request.query_params.get("limit", 100)

        if symbol:
            queryset = queryset.filter(symbol__name=symbol)
        if timeframe:
            queryset = queryset.filter(timeframe__code=timeframe)

        return queryset[: int(limit)]


class LivePriceListView(generics.ListAPIView):
    queryset = LivePrice.objects.select_related("symbol").all()
    serializer_class = LivePriceSerializer
    permission_classes = [permissions.AllowAny]


class LivePriceDetailView(generics.RetrieveAPIView):
    queryset = LivePrice.objects.all()
    serializer_class = LivePriceSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        symbol_name = self.kwargs.get("symbol")
        return LivePrice.objects.select_related("symbol").get(symbol__name=symbol_name)


class EconomicCalendarListView(generics.ListAPIView):
    queryset = EconomicCalendar.objects.all()
    serializer_class = EconomicCalendarSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = EconomicCalendar.objects.all()
        currency = self.request.query_params.get("currency")
        impact = self.request.query_params.get("impact")
        if currency:
            queryset = queryset.filter(currency=currency)
        if impact:
            queryset = queryset.filter(impact_level=impact)
        return queryset


class MarketSentimentListView(generics.ListAPIView):
    serializer_class = MarketSentimentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = MarketSentiment.objects.all()
        symbol = self.request.query_params.get("symbol")
        if symbol:
            queryset = queryset.filter(symbol__name=symbol)
        return queryset


class MarketOverviewView(APIView):
    """Get market overview with live prices and sentiment"""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        prices = LivePrice.objects.select_related("symbol").all()[:20]
        upcoming_events = EconomicCalendar.objects.filter(impact_level__in=["HIGH", "VERY_HIGH"])[:5]

        return Response(
            {
                "prices": LivePriceSerializer(prices, many=True).data,
                "upcoming_events": EconomicCalendarSerializer(upcoming_events, many=True).data,
            }
        )
