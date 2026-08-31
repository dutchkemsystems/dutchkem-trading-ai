import asyncio
import json
import logging
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("market_data")


class MarketDataConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time price streaming from MT5.
    Subscribes to MT5 tick data and broadcasts to connected clients.
    """

    async def connect(self):
        self.symbol = self.scope["url_route"]["kwargs"]["symbol"]
        self.room_group_name = f"market_{self.symbol}"
        self._last_heartbeat = time.time()
        self._is_subscribed = False

        # Connection limit per user
        from django.core.cache import cache
        user_key = f"ws_connections_{self.scope.get('user', {}).get('id', 'anonymous')}"
        current_connections = cache.get(user_key, 0)
        if current_connections >= 5:  # Max 5 connections per user
            await self.close()
            return
        cache.set(user_key, current_connections + 1, timeout=300)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "data": {
                "symbol": self.symbol,
                "server_time": time.time(),
            },
        }))

        prices = await self.get_live_prices(self.symbol)
        if prices:
            await self.send(text_data=json.dumps({
                "type": "initial_prices",
                "data": prices,
            }))

        await self._subscribe_to_mt5_ticks()

    async def disconnect(self, close_code):
        # Decrement connection counter
        from django.core.cache import cache
        user_key = f"ws_connections_{self.scope.get('user', {}).get('id', 'anonymous')}"
        current_connections = cache.get(user_key, 0)
        if current_connections > 0:
            cache.set(user_key, current_connections - 1, timeout=300)

        await self._unsubscribe_from_mt5_ticks()
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info("Client disconnected from %s: %s", self.symbol, close_code)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get("type", "")

            if msg_type == "ping":
                self._last_heartbeat = time.time()
                await self.send(text_data=json.dumps({"type": "pong"}))

            elif msg_type == "subscribe":
                additional = data.get("symbols", [])
                for sym in additional:
                    await self._subscribe_to_mt5_ticks(sym)

            elif msg_type == "unsubscribe":
                symbols = data.get("symbols", [])
                for sym in symbols:
                    await self._unsubscribe_from_mt5_ticks(sym)

            elif msg_type == "get_candles":
                symbol = data.get("symbol", self.symbol)
                timeframe = data.get("timeframe", "M5")
                count = data.get("count", 100)
                candles = await self._get_candles(symbol, timeframe, count)
                await self.send(text_data=json.dumps({
                    "type": "candles",
                    "data": {"symbol": symbol, "timeframe": timeframe, "candles": candles},
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "type": "error",
                "data": {"message": "Invalid JSON"},
            }))

    async def price_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "price_update",
            "data": event["data"],
        }))

    async def signal_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "signal_update",
            "data": event["data"],
        }))

    async def tick_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "tick",
            "data": event["data"],
        }))

    async def _subscribe_to_mt5_ticks(self, symbol=None):
        sym = symbol or self.symbol
        try:
            from mcp_integration.services import mt5_service
            if mt5_service.is_connected:
                await mt5_service.subscribe_ticks(sym)
                self._is_subscribed = True
                logger.info("Subscribed to MT5 ticks: %s", sym)
        except Exception as e:
            logger.error("Failed to subscribe to MT5 ticks for %s: %s", sym, e)

    async def _unsubscribe_from_mt5_ticks(self, symbol=None):
        sym = symbol or self.symbol
        try:
            from mcp_integration.services import mt5_service
            if mt5_service.is_connected:
                await mt5_service.unsubscribe_ticks(sym)
                self._is_subscribed = False
        except Exception as e:
            logger.error("Failed to unsubscribe from MT5 ticks for %s: %s", sym, e)

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
                "last_update": price.last_update.isoformat() if price.last_update else None,
            }
        except Exception:
            return None

    @database_sync_to_async
    def _get_candles(self, symbol, timeframe, count):
        from market_data.models import MarketData
        from trading.models import Symbol

        try:
            sym = Symbol.objects.get(name=symbol)
            tf_map = {"M5": "M5", "M15": "M15", "M30": "M30", "H1": "H1", "H2": "H2", "H4": "H4"}
            tf_code = tf_map.get(timeframe, "H1")

            from indicators.models import Timeframe
            tf = Timeframe.objects.get(code=tf_code)
            candles = MarketData.objects.filter(
                symbol=sym, timeframe=tf
            ).order_by("-timestamp")[:count]

            return [
                {
                    "time": c.timestamp.isoformat(),
                    "open": str(c.open),
                    "high": str(c.high),
                    "low": str(c.low),
                    "close": str(c.close),
                    "volume": c.volume,
                }
                for c in reversed(candles)
            ]
        except Exception:
            return []


class SignalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "signals"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def signal_generated(self, event):
        await self.send(text_data=json.dumps({
            "type": "signal_generated",
            "data": event["data"],
        }))

    async def confluence_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "confluence_update",
            "data": event["data"],
        }))


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

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def trade_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "trade_update",
            "data": event["data"],
        }))

    async def order_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "order_update",
            "data": event["data"],
        }))


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

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def portfolio_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "portfolio_update",
            "data": event["data"],
        }))

    async def risk_alert(self, event):
        await self.send(text_data=json.dumps({
            "type": "risk_alert",
            "data": event["data"],
        }))
