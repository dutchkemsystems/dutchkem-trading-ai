from django.urls import path
from . import views

urlpatterns = [
    path("predict/", views.PredictView.as_view(), name="ml_predict"),
    path("models/", views.ModelListView.as_view(), name="ml_models"),
    path("train/", views.TrainView.as_view(), name="ml_train"),
    # V6.5 Orchestrator (PRIMARY)
    path("v65/status/", views.V65OrchestratorStatusView.as_view(), name="v65-orchestrator-status"),
    path("v65/cycle/", views.V65CycleView.as_view(), name="v65-trigger-cycle"),
    # V6 Orchestrator (LEGACY fallback — kept for backward compatibility)
    path("v6/status/", views.V6OrchestratorStatusView.as_view(), name="v6-orchestrator-status"),
    path("v6/cycle/", views.V6CycleView.as_view(), name="v6-trigger-cycle"),
]
