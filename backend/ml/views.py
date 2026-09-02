from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class PredictView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        symbol = request.data.get("symbol")
        timeframe = request.data.get("timeframe", "H1")
        ohlcv_data = request.data.get("ohlcv_data")

        if not symbol or not ohlcv_data:
            return Response(
                {"error": "symbol and ohlcv_data are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from ml.inference import prediction_service

        result = prediction_service.predict(symbol, timeframe, ohlcv_data)
        return Response(result)


class ModelListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        import os

        model_dir = "model_registry"
        models = []
        if os.path.exists(model_dir):
            for f in os.listdir(model_dir):
                if f.endswith((".h5", ".pkl", ".joblib")):
                    models.append(
                        {
                            "name": f,
                            "size": os.path.getsize(os.path.join(model_dir, f)),
                            "modified": os.path.getmtime(os.path.join(model_dir, f)),
                        }
                    )
        return Response({"models": models})


class TrainView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        model_type = request.data.get("model_type", "lstm")
        # Queue training as Celery task
        from config.tasks import train_model

        task = train_model.delay(model_type)
        return Response(
            {
                "status": "training_queued",
                "task_id": task.id,
                "model_type": model_type,
            }
        )


class V6OrchestratorStatusView(APIView):
    """
    GET /api/v1/ml/v6/status/
    LEGACY — Returns V6 fallback orchestrator status.
    Use /api/v1/ml/v65/status/ for the primary V6.5 engine.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from ml.v6_orchestrator import get_v6_orchestrator

        orchestrator = get_v6_orchestrator()
        status_data = orchestrator.get_status()

        return Response({
            "v6_status": status_data,
            "message": "V6 (legacy fallback) Orchestrator status — use /api/v1/ml/v65/status/ for V6.5",
        })


class V6CycleView(APIView):
    """
    POST /api/v1/ml/v6/cycle/
    LEGACY — Manually trigger a trading cycle (admin only).
    The underlying task runs V6.5 with V6 fallback.
    Use /api/v1/ml/v65/cycle/ for the primary endpoint.
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from config.tasks import run_v6_trading_cycle

        task = run_v6_trading_cycle.delay()
        return Response({
            "status": "cycle_triggered",
            "task_id": task.id,
            "message": "Trading cycle queued (runs V6.5 with fallback)",
        })


class V65OrchestratorStatusView(APIView):
    """
    GET /api/v1/ml/v65/status/
    Returns the current status of the V6.5 Trading Orchestrator (PRIMARY),
    including which components are loaded and available.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from ml.v65_orchestrator import get_v65_orchestrator

        orchestrator = get_v65_orchestrator()
        status_data = orchestrator.get_status()

        return Response({
            "v65_status": status_data,
            "message": "V6.5 Trading Orchestrator status (PRIMARY engine)",
        })


class V65CycleView(APIView):
    """
    POST /api/v1/ml/v65/cycle/
    Manually trigger a V6.5 trading cycle (admin only).
    Typically runs automatically via Celery every 60s.
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from config.tasks import run_v6_trading_cycle

        task = run_v6_trading_cycle.delay()
        return Response({
            "status": "cycle_triggered",
            "task_id": task.id,
            "message": "V6.5 trading cycle queued",
        })
