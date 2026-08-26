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
        return SignalHistory.objects.filter(signal__user=self.request.user)[:100]


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
        serializer = SignalGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # This would trigger the AI signal generation pipeline
        # Using @devhive orchestration, @gstack agents, @minimax generation
        return Response(
            {
                "status": "signal_generation_queued",
                "symbol": serializer.validated_data["symbol"],
                "timeframe": serializer.validated_data["timeframe"],
            }
        )


class ActiveSignalsView(APIView):
    """Get all active signals for the user"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        signals = Signal.objects.filter(is_active=True).order_by("-strength")[:20]
        return Response(SignalSerializer(signals, many=True).data)
