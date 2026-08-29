import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp
import websockets
from django.conf import settings

logger = logging.getLogger("mcp_integration")


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "closed"  # closed = normal, open = blocking, half_open = testing
        self.last_failure_time = None

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning("Circuit breaker OPEN - MT5 requests will be blocked")

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def allow_request(self):
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                return True
            return False
        return True  # half_open allows one request


class MT5ConnectionConfig:
    def __init__(self):
        self.host = getattr(settings, "MT5_HOST", "localhost")
        self.http_port = getattr(settings, "MT5_PORT", 3000)
        self.ws_port = getattr(settings, "MT5_WS_PORT", 3001)
        self.timeout = getattr(settings, "MT5_TIMEOUT", 10)
        self.max_retries = getattr(settings, "MT5_MAX_RETRIES", 5)
        self.retry_delay = getattr(settings, "MT5_RETRY_DELAY", 2.0)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.http_port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.ws_port}"


class MT5Service:
    """
    Service layer for MT5 communication via SYNX-MT5-MCP.
    Provides async HTTP/WebSocket methods for all MT5 operations.
    """

    _instance: Optional["MT5Service"] = None

    def __init__(self):
        self.config = MT5ConnectionConfig()
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._ws_connection = None
        self._is_connected = False
        self._connected_at: Optional[float] = None
        self._request_count = 0
        self._error_count = 0
        self._total_latency = 0.0
        self.circuit_breaker = CircuitBreaker()

    @classmethod
    def get_instance(cls) -> "MT5Service":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "connected": self._is_connected,
            "uptime": round(time.time() - self._connected_at, 1) if self._connected_at else 0,
            "requests": self._request_count,
            "errors": self._error_count,
            "avg_latency_ms": round(
                self._total_latency / self._request_count, 2
            ) if self._request_count > 0 else 0,
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._http_session

    async def _request(
        self, method: str, path: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker is OPEN - MT5 requests blocked")

        session = await self._get_session()
        url = f"{self.config.base_url}{path}"
        start = time.time()

        try:
            if method == "GET":
                async with session.get(url, params=data) as resp:
                    latency = (time.time() - start) * 1000
                    self._request_count += 1
                    self._total_latency += latency
                    body = await resp.json()
                    self.circuit_breaker.record_success()
                    return body
            else:
                async with session.request(method, url, json=data) as resp:
                    latency = (time.time() - start) * 1000
                    self._request_count += 1
                    self._total_latency += latency
                    body = await resp.json()
                    self.circuit_breaker.record_success()
                    return body
        except aiohttp.ClientError as e:
            self._error_count += 1
            self.circuit_breaker.record_failure()
            logger.error("MT5 HTTP error: %s %s — %s", method, path, e)
            raise
        except Exception as e:
            self._error_count += 1
            self.circuit_breaker.record_failure()
            logger.error("MT5 request error: %s %s — %s", method, path, e)
            raise

    async def connect(self) -> Dict[str, Any]:
        for attempt in range(self.config.max_retries):
            try:
                result = await self._request("POST", "/connect", {
                    "command": "connect",
                    "params": {},
                })
                if result.get("success") or result.get("status") == "connected":
                    self._is_connected = True
                    self._connected_at = time.time()
                    logger.info("MT5 connected at %s", self.config.base_url)
                    return {"success": True, "data": result}
            except Exception as e:
                logger.warning(
                    "MT5 connect attempt %d/%d failed: %s",
                    attempt + 1, self.config.max_retries, e,
                )
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        logger.error("MT5 connection failed after %d attempts", self.config.max_retries)
        return {"success": False, "error": "Connection failed"}

    async def disconnect(self) -> Dict[str, Any]:
        try:
            if self._ws_connection and not self._ws_connection.closed:
                await self._ws_connection.close()
                self._ws_connection = None
            await self._request("POST", "/disconnect", {"command": "disconnect"})
        except Exception as e:
            logger.warning("MT5 disconnect error: %s", e)
        finally:
            self._is_connected = False
            self._connected_at = None
        return {"success": True}

    async def health_check(self) -> Dict[str, Any]:
        start = time.time()
        try:
            result = await self._request("GET", "/health", {})
            latency = (time.time() - start) * 1000
            return {
                "status": "healthy" if result.get("success") else "unhealthy",
                "connected": self._is_connected,
                "latency_ms": round(latency, 2),
                "stats": self.stats,
            }
        except Exception as e:
            return {"status": "unreachable", "connected": False, "error": str(e)}

    async def get_account_info(self) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/get_account_info", {
            "tool": "get_account_info",
            "params": {},
        })
        return result.get("result") or result.get("data") or result

    async def get_positions(self) -> List[Dict[str, Any]]:
        result = await self._request("POST", "/tools/get_positions", {
            "tool": "get_positions",
            "params": {},
        })
        data = result.get("result") or result.get("data") or result
        return data.get("positions", []) if isinstance(data, dict) else data

    async def get_orders(self) -> List[Dict[str, Any]]:
        result = await self._request("POST", "/tools/get_orders", {
            "tool": "get_orders",
            "params": {},
        })
        data = result.get("result") or result.get("data") or result
        return data.get("orders", []) if isinstance(data, dict) else data

    async def get_symbols(self) -> List[Dict[str, Any]]:
        result = await self._request("POST", "/tools/get_symbols", {
            "tool": "get_symbols",
            "params": {},
        })
        data = result.get("result") or result.get("data") or result
        return data.get("symbols", []) if isinstance(data, dict) else data

    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/get_symbol_info", {
            "tool": "get_symbol_info",
            "params": {"symbol": symbol},
        })
        return result.get("result") or result.get("data") or result

    async def get_candles(
        self, symbol: str, timeframe: str, count: int = 100
    ) -> List[Dict[str, Any]]:
        result = await self._request("POST", "/tools/get_candles", {
            "tool": "get_candles",
            "params": {"symbol": symbol, "timeframe": timeframe, "count": count},
        })
        data = result.get("result") or result.get("data") or result
        return data.get("candles", []) if isinstance(data, dict) else data

    async def get_tick_data(self, symbol: str) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/get_tick_data", {
            "tool": "get_tick_data",
            "params": {"symbol": symbol},
        })
        return result.get("result") or result.get("data") or result

    async def open_position(
        self,
        symbol: str,
        volume: float,
        position_type: str,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        magic: int = 123456,
        comment: str = "Dutchkem AI",
    ) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/open_position", {
            "tool": "open_position",
            "params": {
                "symbol": symbol,
                "volume": volume,
                "type": position_type.upper(),
                "sl": stop_loss,
                "tp": take_profit,
                "magic": magic,
                "comment": comment,
            },
        })
        data = result.get("result") or result.get("data") or result
        success = isinstance(data, dict) and data.get("ticket") is not None
        return {"success": success, "data": data, "error": None if success else "Order failed"}

    async def close_position(self, ticket: int) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/close_position", {
            "tool": "close_position",
            "params": {"ticket": ticket},
        })
        data = result.get("result") or result.get("data") or result
        return {"success": True, "data": data}

    async def modify_position(
        self, ticket: int, stop_loss: float = 0.0, take_profit: float = 0.0
    ) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/modify_position", {
            "tool": "modify_position",
            "params": {"ticket": ticket, "sl": stop_loss, "tp": take_profit},
        })
        data = result.get("result") or result.get("data") or result
        return {"success": True, "data": data}

    async def place_pending_order(
        self,
        symbol: str,
        volume: float,
        order_type: str,
        position_type: str,
        price: float,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
    ) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/place_order", {
            "tool": "place_order",
            "params": {
                "symbol": symbol,
                "volume": volume,
                "order_type": order_type.upper(),
                "type": position_type.upper(),
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
            },
        })
        data = result.get("result") or result.get("data") or result
        return {"success": True, "data": data}

    async def cancel_order(self, ticket: int) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/cancel_order", {
            "tool": "cancel_order",
            "params": {"ticket": ticket},
        })
        data = result.get("result") or result.get("data") or result
        return {"success": True, "data": data}

    async def get_trade_history(self, days: int = 30) -> List[Dict[str, Any]]:
        result = await self._request("POST", "/tools/get_trade_history", {
            "tool": "get_trade_history",
            "params": {"days": days},
        })
        data = result.get("result") or result.get("data") or result
        return data.get("trades", []) if isinstance(data, dict) else data

    async def get_performance_stats(self) -> Dict[str, Any]:
        result = await self._request("POST", "/tools/get_performance_stats", {
            "tool": "get_performance_stats",
            "params": {},
        })
        return result.get("result") or result.get("data") or result

    async def subscribe_ticks(self, symbol: str, callback=None):
        if not self._ws_connection or self._ws_connection.closed:
            self._ws_connection = await websockets.connect(
                self.config.ws_url,
                ping_interval=20,
                ping_timeout=10,
            )
        await self._ws_connection.send(json.dumps({
            "command": "subscribe_ticks",
            "symbol": symbol,
        }))
        logger.info("Subscribed to ticks: %s", symbol)

    async def unsubscribe_ticks(self, symbol: str):
        if self._ws_connection and not self._ws_connection.closed:
            await self._ws_connection.send(json.dumps({
                "command": "unsubscribe_ticks",
                "symbol": symbol,
            }))

    async def close(self):
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        if self._ws_connection and not self._ws_connection.closed:
            await self._ws_connection.close()


mt5_service = MT5Service.get_instance()
