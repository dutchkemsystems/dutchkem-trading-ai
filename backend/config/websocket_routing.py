from django.urls import re_path

from market_data import consumers

websocket_urlpatterns = [
    re_path(r"ws/market-data/(?P<symbol>\w+)/$", consumers.MarketDataConsumer.as_asgi()),
    re_path(r"ws/signals/$", consumers.SignalConsumer.as_asgi()),
    re_path(r"ws/trades/$", consumers.TradeConsumer.as_asgi()),
    re_path(r"ws/portfolio/$", consumers.PortfolioConsumer.as_asgi()),
]
