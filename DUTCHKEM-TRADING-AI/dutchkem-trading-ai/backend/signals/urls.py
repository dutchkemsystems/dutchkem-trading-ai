from django.urls import path

from . import views

urlpatterns = [
    path("", views.SignalListView.as_view(), name="signal_list"),
    path("<uuid:pk>/", views.SignalDetailView.as_view(), name="signal_detail"),
    path("history/", views.SignalHistoryView.as_view(), name="signal_history"),
    path("confluence/", views.ConfluenceScoreListView.as_view(), name="confluence_score_list"),
    path("generate/", views.SignalGenerateView.as_view(), name="signal_generate"),
    path("active/", views.ActiveSignalsView.as_view(), name="active_signals"),
]
