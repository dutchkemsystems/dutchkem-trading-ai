import logging
import time
from typing import Any, Dict, List, Optional

from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

logger = logging.getLogger("market_data")


class PriceDataService:
    """
    Service for streaming and managing price data from MT5.
    Handles price updates, storage, and WebSocket broadcasting.
    """

    _instance: Optional["PriceDataService"] = None

    def __init__(self):
        self._channel_layer = None
        self._last_prices: Dict[str, Dict[str, Any]] = {}
        self._update_count = 0

    @classmethod
    def get_instance(cls) -> "PriceDataService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def channel_layer(self):
        if self._channel_layer is None:
            self._channel_layer = get_channel_layer()
        return self._channel_layer

    async def fetch_and_broadcast_prices(self, symbols: Optional[List[str]] = None):
        from mcp_integration.services import mt5_service

        if not mt5_service.is_connected:
            logger.warning("MT5 not connected, skipping price fetch")
            return

        if symbols is None:
            symbols = await self._get_active_symbols()

        for symbol in symbols:
            try:
                tick = await mt5_service.get_tick_data(symbol)
                if tick:
                    await self._process_tick(symbol, tick)
            except Exception as e:
                logger.error("Error fetching price for %s: %s", symbol, e)

    async def _process_tick(self, symbol: str, tick: Dict[str, Any]):
        price_data = {
            "symbol": symbol,
            "bid": tick.get("bid", 0),
            "ask": tick.get("ask", 0),
            "spread": tick.get("spread", 0),
            "last": tick.get("last", tick.get("bid", 0)),
            "volume": tick.get("volume", 0),
            "timestamp": time.time(),
        }

        self._last_prices[symbol] = price_data
        self._update_count += 1

        await self._store_price(price_data)
        await self._broadcast_price(symbol, price_data)

    async def _store_price(self, price_data: Dict[str, Any]):
        from market_data.models import LivePrice
        from trading.models import Symbol

        try:
            sym = Symbol.objects.get(name=price_data["symbol"])
            LivePrice.objects.update_or_create(
                symbol=sym,
                defaults={
                    "bid": price_data["bid"],
                    "ask": price_data["ask"],
                    "spread": price_data["spread"],
                },
            )
        except Symbol.DoesNotExist:
            logger.warning("Symbol not found: %s", price_data["symbol"])
        except Exception as e:
            logger.error("Error storing price: %s", e)

    async def _broadcast_price(self, symbol: str, price_data: Dict[str, Any]):
        try:
            await self.channel_layer.group_send(
                f"market_{symbol}",
                {
                    "type": "price_update",
                    "data": price_data,
                },
            )
        except Exception as e:
            logger.error("Error broadcasting price for %s: %s", symbol, e)

    async def broadcast_signal(self, signal_data: Dict[str, Any]):
        try:
            await self.channel_layer.group_send(
                "signals",
                {
                    "type": "signal_generated",
                    "data": signal_data,
                },
            )
        except Exception as e:
            logger.error("Error broadcasting signal: %s", e)

    async def broadcast_trade_update(self, user_id: int, trade_data: Dict[str, Any]):
        try:
            await self.channel_layer.group_send(
                f"trades_{user_id}",
                {
                    "type": "trade_update",
                    "data": trade_data,
                },
            )
        except Exception as e:
            logger.error("Error broadcasting trade update: %s", e)

    async def broadcast_portfolio_update(self, user_id: int, portfolio_data: Dict[str, Any]):
        try:
            await self.channel_layer.group_send(
                f"portfolio_{user_id}",
                {
                    "type": "portfolio_update",
                    "data": portfolio_data,
                },
            )
        except Exception as e:
            logger.error("Error broadcasting portfolio update: %s", e)

    async def broadcast_risk_alert(self, user_id: int, alert_data: Dict[str, Any]):
        try:
            await self.channel_layer.group_send(
                f"portfolio_{user_id}",
                {
                    "type": "risk_alert",
                    "data": alert_data,
                },
            )
        except Exception as e:
            logger.error("Error broadcasting risk alert: %s", e)

    def get_last_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self._last_prices.get(symbol)

    def get_all_prices(self) -> Dict[str, Dict[str, Any]]:
        return self._last_prices.copy()

    @database_sync_to_async
    def _get_active_symbols(self) -> List[str]:
        from trading.models import Symbol
        return list(Symbol.objects.filter(is_active=True).values_list("name", flat=True))


price_service = PriceDataService.get_instance()
