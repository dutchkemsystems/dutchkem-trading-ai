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
