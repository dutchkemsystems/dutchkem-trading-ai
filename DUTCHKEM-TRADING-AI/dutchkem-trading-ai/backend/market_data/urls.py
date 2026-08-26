from django.urls import path

from . import views

urlpatterns = [
    path("", views.MarketDataListView.as_view(), name="market_data_list"),
    path("live/", views.LivePriceListView.as_view(), name="live_price_list"),
    path("live/<str:symbol>/", views.LivePriceDetailView.as_view(), name="live_price_detail"),
    path("calendar/", views.EconomicCalendarListView.as_view(), name="economic_calendar"),
    path("sentiment/", views.MarketSentimentListView.as_view(), name="market_sentiment"),
    path("overview/", views.MarketOverviewView.as_view(), name="market_overview"),
]
