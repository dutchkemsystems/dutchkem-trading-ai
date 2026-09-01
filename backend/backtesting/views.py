from rest_framework import generics, permissions

from .models import BacktestResult
from .serializers import BacktestResultSerializer


class BacktestResultListView(generics.ListAPIView):
    serializer_class = BacktestResultSerializer

    def get_queryset(self):
        return BacktestResult.objects.filter(user=self.request.user)


class BacktestResultDetailView(generics.RetrieveAPIView):
    serializer_class = BacktestResultSerializer

    def get_queryset(self):
        return BacktestResult.objects.filter(user=self.request.user)


class RunBacktestView(generics.CreateAPIView):
    serializer_class = BacktestResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        from config.tasks import run_backtest

        instance = serializer.save(user=self.request.user)
        run_backtest.delay(str(instance.id))
