import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

import aiohttp
import websockets

logger = logging.getLogger("mcp_service")


class MCPServerType(Enum):
    SYNX_MT5 = "synx-mt5-mcp"
    AKTOOLS = "aktools-pro"
    OPENALGO = "openalgo"
    CROSSSTRADE = "crosstrade"
    OPENTRADING = "open-trading"


@dataclass
class MCPToolResult:
    success: bool
    data: Any
    error: Optional[str] = None
    server: str = ""
    tool: str = ""
    latency_ms: float = 0.0


@dataclass
class MT5ConnectionConfig:
    host: str = "localhost"
    http_port: int = 3000
    ws_port: int = 3001
    timeout: int = 10
    max_retries: int = 5
    retry_delay: float = 2.0
    health_check_interval: float = 30.0


class MT5ConnectionError(Exception):
    pass


class MT5TimeoutError(MT5ConnectionError):
    pass


class MT5OrderError(MT5ConnectionError):
    pass


class MCPMT5Client:
    """
    Real HTTP/WebSocket client for MT5 via SYNX-MT5-MCP protocol.
    Handles REST commands and real-time tick data streaming.
    """

    def __init__(self, config: Optional[MT5ConnectionConfig] = None):
        self.config = config or MT5ConnectionConfig()
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._ws_connection: Optional[websockets.WebSocketClientProtocol] = None
        self._is_connected = False
        self._connected_at: Optional[float] = None
        self._last_health_check: float = 0.0
        self._request_count: int = 0
        self._error_count: int = 0
        self._total_latency: float = 0.0
        self._subscribed_symbols: set = set()
        self._tick_listeners: Dict[str, List] = {}

    @property
    def base_url(self) -> str:
        return f"http://{self.config.host}:{self.config.http_port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.config.host}:{self.config.ws_port}"

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def avg_latency_ms(self) -> float:
        if self._request_count == 0:
            return 0.0
        return self._total_latency / self._request_count

    @property
    def uptime_seconds(self) -> float:
        if self._connected_at is None:
            return 0.0
        return time.time() - self._connected_at

    async def connect(self) -> bool:
        for attempt in range(self.config.max_retries):
            try:
                self._http_session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    headers={"Content-Type": "application/json"},
                )
                result = await self._http_request("POST", "/connect", {
                    "command": "connect",
                    "params": {}
                })
                if result.get("success") or result.get("status") == "connected":
                    self._is_connected = True
                    self._connected_at = time.time()
                    logger.info("MT5 connected via SYNX-MT5-MCP at %s", self.base_url)
                    return True
                else:
                    logger.warning("MT5 connect returned: %s", result)
            except Exception as e:
                logger.warning("MT5 connection attempt %d failed: %s", attempt + 1, e)
            finally:
                if self._http_session and self._http_session.closed:
                    await self._http_session.close()
                    self._http_session = None

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        logger.error("MT5 connection failed after %d attempts", self.config.max_retries)
        return False

    async def disconnect(self):
        try:
            if self._ws_connection:
                await self._ws_connection.close()
                self._ws_connection = None
            if self._http_session and not self._http_session.closed:
                await self._http_request("POST", "/disconnect", {"command": "disconnect"})
        except Exception as e:
            logger.warning("Error during MT5 disconnect: %s", e)
        finally:
            self._is_connected = False
            self._connected_at = None
            self._subscribed_symbols.clear()
            if self._http_session and not self._http_session.closed:
                await self._http_session.close()
            self._http_session = None

    async def health_check(self) -> Dict[str, Any]:
        start = time.time()
        try:
            result = await self._http_request("GET", "/health", {})
            latency = (time.time() - start) * 1000
            self._last_health_check = time.time()
            return {
                "status": "healthy" if result.get("success") else "unhealthy",
                "connected": self._is_connected,
                "latency_ms": round(latency, 2),
                "uptime_seconds": round(self.uptime_seconds, 1),
                "request_count": self._request_count,
                "error_count": self._error_count,
                "avg_latency_ms": round(self.avg_latency_ms, 2),
                "server": result.get("server", {}),
            }
        except Exception as e:
            self._error_count += 1
            return {
                "status": "unreachable",
                "connected": False,
                "error": str(e),
            }

    async def get_account_info(self) -> MCPToolResult:
        data = await self._call_tool("get_account_info")
        return MCPToolResult(
            success=data is not None,
            data=data or {},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_account_info",
        )

    async def get_symbol_info(self, symbol: str) -> MCPToolResult:
        data = await self._call_tool("get_symbol_info", {"symbol": symbol})
        return MCPToolResult(
            success=data is not None,
            data=data or {},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_symbol_info",
        )

    async def get_symbols(self) -> MCPToolResult:
        data = await self._call_tool("get_symbols", {})
        return MCPToolResult(
            success=data is not None,
            data=data or {"symbols": []},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_symbols",
        )

    async def get_candles(
        self, symbol: str, timeframe: str, count: int = 100
    ) -> MCPToolResult:
        data = await self._call_tool("get_candles", {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": count,
        })
        return MCPToolResult(
            success=data is not None,
            data=data or {"candles": []},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_candles",
        )

    async def get_tick_data(self, symbol: str) -> MCPToolResult:
        data = await self._call_tool("get_tick_data", {"symbol": symbol})
        return MCPToolResult(
            success=data is not None,
            data=data or {},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_tick_data",
        )

    async def get_positions(self) -> MCPToolResult:
        data = await self._call_tool("get_positions", {})
        return MCPToolResult(
            success=data is not None,
            data=data or {"positions": []},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_positions",
        )

    async def get_orders(self) -> MCPToolResult:
        data = await self._call_tool("get_orders", {})
        return MCPToolResult(
            success=data is not None,
            data=data or {"orders": []},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_orders",
        )

    async def open_position(
        self,
        symbol: str,
        volume: float,
        position_type: str,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        magic: int = 123456,
        comment: str = "Dutchkem AI",
    ) -> MCPToolResult:
        params = {
            "symbol": symbol,
            "volume": volume,
            "type": position_type.upper(),
            "sl": stop_loss,
            "tp": take_profit,
            "magic": magic,
            "comment": comment,
        }
        data = await self._call_tool("open_position", params)
        success = data is not None and data.get("ticket") is not None
        return MCPToolResult(
            success=success,
            data=data or {},
            error=None if success else "Order execution failed",
            server=MCPServerType.SYNX_MT5.value,
            tool="open_position",
        )

    async def close_position(self, ticket: int) -> MCPToolResult:
        data = await self._call_tool("close_position", {"ticket": ticket})
        return MCPToolResult(
            success=data is not None and data.get("status") == "closed",
            data=data or {},
            server=MCPServerType.SYNX_MT5.value,
            tool="close_position",
        )

    async def modify_position(
        self, ticket: int, stop_loss: float = 0.0, take_profit: float = 0.0
    ) -> MCPToolResult:
        data = await self._call_tool("modify_position", {
            "ticket": ticket,
            "sl": stop_loss,
            "tp": take_profit,
        })
        return MCPToolResult(
            success=data is not None,
            data=data or {},
            server=MCPServerType.SYNX_MT5.value,
            tool="modify_position",
        )

    async def place_order(
        self,
        symbol: str,
        volume: float,
        order_type: str,
        position_type: str,
        price: float,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
    ) -> MCPToolResult:
        params = {
            "symbol": symbol,
            "volume": volume,
            "order_type": order_type.upper(),
            "type": position_type.upper(),
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
        }
        data = await self._call_tool("place_order", params)
        return MCPToolResult(
            success=data is not None and data.get("ticket") is not None,
            data=data or {},
            server=MCPServerType.SYNX_MT5.value,
            tool="place_order",
        )

    async def cancel_order(self, ticket: int) -> MCPToolResult:
        data = await self._call_tool("cancel_order", {"ticket": ticket})
        return MCPToolResult(
            success=data is not None,
            data=data or {},
            server=MCPServerType.SYNX_MT5.value,
            tool="cancel_order",
        )

    async def get_trade_history(
        self, days: int = 30
    ) -> MCPToolResult:
        data = await self._call_tool("get_trade_history", {"days": days})
        return MCPToolResult(
            success=data is not None,
            data=data or {"trades": []},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_trade_history",
        )

    async def get_performance_stats(self) -> MCPToolResult:
        data = await self._call_tool("get_performance_stats", {})
        return MCPToolResult(
            success=data is not None,
            data=data or {},
            server=MCPServerType.SYNX_MT5.value,
            tool="get_performance_stats",
        )

    async def subscribe_ticks(self, symbol: str, callback=None):
        if symbol in self._subscribed_symbols:
            return
        self._subscribed_symbols.add(symbol)
        if callback:
            self._tick_listeners.setdefault(symbol, []).append(callback)
        try:
            if not self._ws_connection or self._ws_connection.closed:
                self._ws_connection = await websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                )
            await self._ws_connection.send(json.dumps({
                "command": "subscribe_ticks",
                "symbol": symbol,
            }))
            logger.info("Subscribed to tick data for %s", symbol)
        except Exception as e:
            logger.error("Failed to subscribe to ticks for %s: %s", symbol, e)
            self._subscribed_symbols.discard(symbol)

    async def unsubscribe_ticks(self, symbol: str):
        self._subscribed_symbols.discard(symbol)
        self._tick_listeners.pop(symbol, None)
        if self._ws_connection and not self._ws_connection.closed:
            try:
                await self._ws_connection.send(json.dumps({
                    "command": "unsubscribe_ticks",
                    "symbol": symbol,
                }))
            except Exception:
                pass

    async def receive_ticks(self):
        if not self._ws_connection:
            return
        try:
            async for message in self._ws_connection:
                data = json.loads(message)
                if data.get("type") == "tick":
                    symbol = data.get("symbol")
                    for listener in self._tick_listeners.get(symbol, []):
                        try:
                            await listener(data) if asyncio.iscoroutinefunction(listener) else listener(data)
                        except Exception as e:
                            logger.error("Tick listener error for %s: %s", symbol, e)
        except websockets.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self._is_connected = False
        except Exception as e:
            logger.error("Tick receive error: %s", e)

    async def _http_request(
        self, method: str, path: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self._http_session or self._http_session.closed:
            raise MT5ConnectionError("HTTP session not initialized")

        url = f"{self.base_url}{path}"
        start = time.time()

        try:
            if method == "GET":
                async with self._http_session.get(url, params=payload) as resp:
                    latency = (time.time() - start) * 1000
                    self._request_count += 1
                    self._total_latency += latency
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        text = await resp.text()
                        self._error_count += 1
                        raise MT5ConnectionError(
                            f"HTTP {resp.status}: {text}"
                        )
            else:
                async with self._http_session.request(method, url, json=payload) as resp:
                    latency = (time.time() - start) * 1000
                    self._request_count += 1
                    self._total_latency += latency
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        text = await resp.text()
                        self._error_count += 1
                        raise MT5ConnectionError(
                            f"HTTP {resp.status}: {text}"
                        )
        except aiohttp.ClientError as e:
            self._error_count += 1
            raise MT5ConnectionError(f"HTTP request failed: {e}")

    async def _call_tool(
        self, tool_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        start = time.time()
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                result = await self._http_request("POST", f"/tools/{tool_name}", {
                    "tool": tool_name,
                    "params": params or {},
                })
                latency = (time.time() - start) * 1000
                if latency > 1000:
                    logger.warning(
                        "Slow MCP call %s: %.0fms", tool_name, latency
                    )
                return result.get("result") or result.get("data") or result
            except MT5ConnectionError as e:
                last_error = e
                self._error_count += 1
                logger.warning(
                    "MCP call %s attempt %d failed: %s",
                    tool_name, attempt + 1, e,
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

        logger.error(
            "MCP call %s failed after %d attempts: %s",
            tool_name, self.config.max_retries, last_error,
        )
        return None


import json


class MCPIntegrationService:
    """
    Unified MCP Integration Service with real MT5 connections.
    """

    def __init__(self, config: Optional[MT5ConnectionConfig] = None):
        self.mt5_client = MCPMT5Client(config)
        self._servers: Dict[MCPServerType, Dict[str, Any]] = {}
        self._initialize_servers()

    def _initialize_servers(self):
        self._servers = {
            MCPServerType.SYNX_MT5: {
                "name": "SYNX-MT5-MCP",
                "description": "MetaTrader 5 integration (68+ tools)",
                "connected": False,
            },
        }

    async def connect_mt5(
        self, account: str = "", password: str = "", server: str = ""
    ) -> MCPToolResult:
        connected = await self.mt5_client.connect()
        if connected:
            self._servers[MCPServerType.SYNX_MT5]["connected"] = True
            info = await self.mt5_client.get_account_info()
            return MCPToolResult(
                success=True,
                data={
                    "status": "connected",
                    "account": account,
                    "account_info": info.data,
                },
                server=MCPServerType.SYNX_MT5.value,
                tool="connect_mt5",
            )
        return MCPToolResult(
            success=False,
            data={},
            error="Failed to connect to MT5",
            server=MCPServerType.SYNX_MT5.value,
            tool="connect_mt5",
        )

    async def disconnect_mt5(self) -> MCPToolResult:
        await self.mt5_client.disconnect()
        self._servers[MCPServerType.SYNX_MT5]["connected"] = False
        return MCPToolResult(
            success=True,
            data={"status": "disconnected"},
            server=MCPServerType.SYNX_MT5.value,
            tool="disconnect_mt5",
        )

    async def health_check(self) -> MCPToolResult:
        health = await self.mt5_client.health_check()
        return MCPToolResult(
            success=health.get("status") == "healthy",
            data=health,
            server=MCPServerType.SYNX_MT5.value,
            tool="health_check",
        )

    async def get_account_info(self) -> MCPToolResult:
        return await self.mt5_client.get_account_info()

    async def get_positions(self) -> MCPToolResult:
        return await self.mt5_client.get_positions()

    async def get_orders(self) -> MCPToolResult:
        return await self.mt5_client.get_orders()

    async def get_symbols(self) -> MCPToolResult:
        return await self.mt5_client.get_symbols()

    async def get_symbol_info(self, symbol: str) -> MCPToolResult:
        return await self.mt5_client.get_symbol_info(symbol)

    async def get_candles(
        self, symbol: str, timeframe: str, count: int = 100
    ) -> MCPToolResult:
        return await self.mt5_client.get_candles(symbol, timeframe, count)

    async def get_tick_data(self, symbol: str) -> MCPToolResult:
        return await self.mt5_client.get_tick_data(symbol)

    async def open_position(
        self,
        symbol: str,
        volume: float,
        position_type: str,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        magic: int = 123456,
    ) -> MCPToolResult:
        return await self.mt5_client.open_position(
            symbol, volume, position_type, stop_loss, take_profit, magic
        )

    async def close_position(self, ticket: int) -> MCPToolResult:
        return await self.mt5_client.close_position(ticket)

    async def modify_position(
        self, ticket: int, stop_loss: float = 0.0, take_profit: float = 0.0
    ) -> MCPToolResult:
        return await self.mt5_client.modify_position(ticket, stop_loss, take_profit)

    async def place_order(
        self,
        symbol: str,
        volume: float,
        order_type: str,
        position_type: str,
        price: float,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
    ) -> MCPToolResult:
        return await self.mt5_client.place_order(
            symbol, volume, order_type, position_type, price, stop_loss, take_profit
        )

    async def cancel_order(self, ticket: int) -> MCPToolResult:
        return await self.mt5_client.cancel_order(ticket)

    async def get_trade_history(self, days: int = 30) -> MCPToolResult:
        return await self.mt5_client.get_trade_history(days)

    async def get_performance_stats(self) -> MCPToolResult:
        return await self.mt5_client.get_performance_stats()

    async def subscribe_ticks(self, symbol: str, callback=None):
        await self.mt5_client.subscribe_ticks(symbol, callback)

    async def unsubscribe_ticks(self, symbol: str):
        await self.mt5_client.unsubscribe_ticks(symbol)

    def get_all_servers(self) -> Dict[str, Any]:
        return {
            server_type.value: {
                "name": info["name"],
                "description": info["description"],
                "connected": info["connected"],
            }
            for server_type, info in self._servers.items()
        }


mcp_service = MCPIntegrationService()
