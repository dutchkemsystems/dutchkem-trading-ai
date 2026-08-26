from django.urls import path

from . import views

urlpatterns = [
    path("", views.EAListView.as_view(), name="ea_list"),
    path("<uuid:pk>/", views.ExpertAdvisorDetailView.as_view(), name="ea_detail"),
    path("create/", views.ExpertAdvisorCreateView.as_view(), name="ea_create"),
    path("generate-code/", views.EAGenerateCodeView.as_view(), name="ea_generate_code"),
    path("<uuid:ea_id>/backtest/", views.EABacktestView.as_view(), name="ea_backtest"),
    path("<uuid:ea_id>/deploy/", views.EADeployView.as_view(), name="ea_deploy"),
]
