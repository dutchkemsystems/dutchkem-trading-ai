import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.symbol = self.scope["url_route"]["kwargs"]["symbol"]
        self.room_group_name = f"market_{self.symbol}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Send initial price data
        prices = await self.get_live_prices(self.symbol)
        await self.send(text_data=json.dumps({"type": "initial_prices", "data": prices}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get("type") == "subscribe":
            # Handle subscription to additional symbols
            pass

    async def price_update(self, event):
        await self.send(text_data=json.dumps({"type": "price_update", "data": event["data"]}))

    async def signal_update(self, event):
        await self.send(text_data=json.dumps({"type": "signal_update", "data": event["data"]}))

    @database_sync_to_async
    def get_live_prices(self, symbol):
        from market_data.models import LivePrice
        from trading.models import Symbol

        try:
            sym = Symbol.objects.get(name=symbol)
            price = LivePrice.objects.get(symbol=sym)
            return {
                "symbol": price.symbol.name,
                "bid": str(price.bid),
                "ask": str(price.ask),
                "spread": str(price.spread),
            }
        except:
            return {}


class SignalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "signals"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def signal_generated(self, event):
        await self.send(text_data=json.dumps({"type": "signal_generated", "data": event["data"]}))

    async def confluence_update(self, event):
        await self.send(text_data=json.dumps({"type": "confluence_update", "data": event["data"]}))


class TradeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        self.room_group_name = f"trades_{self.user.id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def trade_update(self, event):
        await self.send(text_data=json.dumps({"type": "trade_update", "data": event["data"]}))

    async def order_update(self, event):
        await self.send(text_data=json.dumps({"type": "order_update", "data": event["data"]}))


class PortfolioConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        self.room_group_name = f"portfolio_{self.user.id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def portfolio_update(self, event):
        await self.send(text_data=json.dumps({"type": "portfolio_update", "data": event["data"]}))

    async def risk_alert(self, event):
        await self.send(text_data=json.dumps({"type": "risk_alert", "data": event["data"]}))
