from django.urls import path
from . import views

urlpatterns = [
    path("predict/", views.PredictView.as_view(), name="ml_predict"),
    path("models/", views.ModelListView.as_view(), name="ml_models"),
    path("train/", views.TrainView.as_view(), name="ml_train"),
]
