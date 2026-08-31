"""
Native MCP Bridge Server for MetaTrader 5
Replaces the Docker synx-mt5-mcp container.
Connects directly to MT5 via the MetaTrader5 Python package.

Runs on port 8080 (same as the Docker container).
"""

import asyncio
import json
import logging
import os
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiohttp import web

logger = logging.getLogger("mcp_bridge")

# ── MetaTrader5 connection ─────────────────────────────────────────
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.error("MetaTrader5 package not installed. Run: pip install MetaTrader5")


class MT5Bridge:
    """Direct MT5 connection via MetaTrader5 Python package."""

    def __init__(self):
        self._connected = False
        self._connected_at: Optional[float] = None
        self._request_count = 0
        self._error_count = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, login: int = 0, password: str = "", server: str = "") -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return {"success": False, "error": "MetaTrader5 package not installed"}

        if self._connected:
            return {"success": True, "status": "already_connected"}

        # Initialize MT5 — try default path first, then common install locations
        if not mt5.initialize():
            # Try common install paths
            mt5_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\MetaTrader 5\terminal64.exe"),
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
            ]
            initialized = False
            for path in mt5_paths:
                if os.path.exists(path):
                    if mt5.initialize(path=path):
                        initialized = True
                        break
            if not initialized:
                error = mt5.last_error()
                return {"success": False, "error": f"MT5 initialize failed: {error}"}

        # Login if credentials provided
        if login and password and server:
            authorized = mt5.login(login, password=password, server=server)
            if not authorized:
                error = mt5.last_error()
                mt5.shutdown()
                return {"success": False, "error": f"MT5 login failed: {error}"}

        self._connected = True
        self._connected_at = time.time()

        account_info = mt5.account_info()
        return {
            "success": True,
            "status": "connected",
            "server": {
                "name": "native-mt5-bridge",
                "version": "1.0.0",
            },
            "account": {
                "login": account_info.login if account_info else 0,
                "name": account_info.name if account_info else "",
                "server": account_info.server if account_info else "",
                "balance": account_info.balance if account_info else 0,
                "equity": account_info.equity if account_info else 0,
                "margin": account_info.margin if account_info else 0,
                "free_margin": account_info.margin_free if account_info else 0,
                "leverage": account_info.leverage if account_info else 0,
                "currency": account_info.currency if account_info else "USD",
            } if account_info else {},
        }

    def disconnect(self) -> Dict[str, Any]:
        if MT5_AVAILABLE and self._connected:
            mt5.shutdown()
        self._connected = False
        self._connected_at = None
        return {"success": True, "status": "disconnected"}

    def health_check(self) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return {"status": "unhealthy", "connected": False, "error": "MetaTrader5 not installed"}

        if not self._connected:
            return {"status": "disconnected", "connected": False}

        account_info = mt5.account_info()
        return {
            "status": "healthy",
            "connected": True,
            "uptime_seconds": round(time.time() - self._connected_at, 1) if self._connected_at else 0,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "account_balance": account_info.balance if account_info else 0,
        }

    def get_account_info(self) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        info = mt5.account_info()
        if info is None:
            return {"error": "Failed to get account info"}
        self._request_count += 1
        return {
            "login": info.login,
            "name": info.name,
            "server": info.server,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "margin_free": info.margin_free,
            "margin_level": info.margin_level,
            "leverage": info.leverage,
            "currency": info.currency,
            "profit": info.profit,
            "company": info.company,
        }

    def get_symbols(self) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        symbols = mt5.symbols_get()
        if symbols is None:
            return {"symbols": []}
        self._request_count += 1
        return {
            "symbols": [
                {
                    "name": s.name,
                    "description": s.description,
                    "group": s.group,
                    "point": s.point,
                    "digits": s.digits,
                    "spread": s.spread,
                    "volume_min": s.volume_min,
                    "volume_max": s.volume_max,
                    "volume_step": s.volume_step,
                }
                for s in symbols
            ]
        }

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        info = mt5.symbol_info(symbol)
        if info is None:
            return {"error": f"Symbol {symbol} not found"}
        self._request_count += 1
        return {
            "name": info.name,
            "description": info.description,
            "point": info.point,
            "digits": info.digits,
            "spread": info.spread,
            "bid": info.bid,
            "ask": info.ask,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "trade_contract_size": info.trade_contract_size,
        }

    def get_candles(self, symbol: str, timeframe: str, count: int = 100) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}

        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H2": mt5.TIMEFRAME_H2,
            "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        }
        tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_M5)

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            return {"candles": []}

        self._request_count += 1
        candles = []
        for r in rates:
            candles.append({
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(r["tick_volume"]),
            })
        return {"candles": candles}

    def get_tick_data(self, symbol: str) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"error": f"No tick data for {symbol}"}
        self._request_count += 1
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": round((tick.ask - tick.bid) / mt5.symbol_info(symbol).point, 1) if mt5.symbol_info(symbol) else 0,
            "time": int(tick.time),
            "volume": tick.volume,
        }

    def get_positions(self) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        positions = mt5.positions_get()
        if positions is None:
            return {"positions": []}
        self._request_count += 1
        return {
            "positions": [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": p.volume,
                    "price_open": p.price_open,
                    "price_current": p.price_current,
                    "sl": p.sl,
                    "tp": p.tp,
                    "profit": p.profit,
                    "swap": p.swap,
                    "magic": p.magic,
                    "comment": p.comment,
                    "time": int(p.time),
                }
                for p in positions
            ]
        }

    def open_position(
        self, symbol: str, volume: float, position_type: str,
        stop_loss: float = 0.0, take_profit: float = 0.0,
        magic: int = 123456, comment: str = "Dutchkem AI",
    ) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"success": False, "error": f"Symbol {symbol} not found"}

        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "error": f"No tick data for {symbol}"}

        order_type = mt5.ORDER_TYPE_BUY if position_type.upper() in ("BUY", "LONG") else mt5.ORDER_TYPE_SELL
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        # Normalize volume
        volume_step = symbol_info.volume_step
        if volume_step > 0:
            volume = max(symbol_info.volume_min, min(symbol_info.volume_max,
                         round(volume / volume_step) * volume_step))

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": 10,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if stop_loss > 0:
            request["sl"] = stop_loss
        if take_profit > 0:
            request["tp"] = take_profit

        result = mt5.order_send(request)
        self._request_count += 1

        if result is None:
            return {"success": False, "error": f"order_send failed: {mt5.last_error()}"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"success": False, "error": f"Order rejected: {result.comment}", "retcode": result.retcode}

        return {
            "success": True,
            "ticket": result.order,
            "volume": volume,
            "price": result.price,
            "symbol": symbol,
            "type": position_type.upper(),
        }

    def close_position(self, ticket: int) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"success": False, "error": f"Position {ticket} not found"}

        pos = position[0]
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": pos.magic,
            "comment": "Dutchkem close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        self._request_count += 1

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"success": False, "error": f"Close failed: {result.comment if result else mt5.last_error()}"}

        return {"success": True, "status": "closed", "ticket": ticket}

    def modify_position(self, ticket: int, stop_loss: float = 0.0, take_profit: float = 0.0) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"success": False, "error": f"Position {ticket} not found"}

        pos = position[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": stop_loss if stop_loss > 0 else pos.sl,
            "tp": take_profit if take_profit > 0 else pos.tp,
        }

        result = mt5.order_send(request)
        self._request_count += 1

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"success": False, "error": f"Modify failed: {result.comment if result else mt5.last_error()}"}

        return {"success": True, "ticket": ticket}

    def get_trade_history(self, days: int = 30) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}

        from datetime import timedelta
        now = datetime.now()
        date_to = now
        date_from = now - timedelta(days=days)

        deals = mt5.history_deals_get(date_from, date_to)
        if deals is None:
            return {"trades": []}

        self._request_count += 1
        return {
            "trades": [
                {
                    "ticket": d.ticket,
                    "order": d.order,
                    "symbol": d.symbol,
                    "type": "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "volume": d.volume,
                    "price": d.price,
                    "profit": d.profit,
                    "swap": d.swap,
                    "commission": d.commission,
                    "time": int(d.time),
                    "comment": d.comment,
                }
                for d in deals
            ]
        }


# ── HTTP API Server ────────────────────────────────────────────────

bridge = MT5Bridge()


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response(bridge.health_check())


async def handle_connect(request: web.Request) -> web.Response:
    data = await request.json()
    params = data.get("params", data)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: bridge.connect(
        login=params.get("login", 0),
        password=params.get("password", ""),
        server=params.get("server", ""),
    ))
    return web.json_response(result)


async def handle_disconnect(request: web.Request) -> web.Response:
    result = bridge.disconnect()
    return web.json_response(result)


async def handle_tool(request: web.Request) -> web.Response:
    tool_name = request.match_info["tool_name"]
    try:
        data = await request.json()
    except Exception:
        data = {}
    params = data.get("params", data)

    try:
        loop = asyncio.get_event_loop()
        if tool_name == "get_account_info":
            result = await loop.run_in_executor(None, bridge.get_account_info)
        elif tool_name == "get_symbols":
            result = await loop.run_in_executor(None, bridge.get_symbols)
        elif tool_name == "get_symbol_info":
            result = await loop.run_in_executor(None, lambda: bridge.get_symbol_info(params.get("symbol", "")))
        elif tool_name == "get_candles":
            result = await loop.run_in_executor(None, lambda: bridge.get_candles(
                params.get("symbol", ""),
                params.get("timeframe", "M5"),
                params.get("count", 100),
            ))
        elif tool_name == "get_tick_data":
            result = await loop.run_in_executor(None, lambda: bridge.get_tick_data(params.get("symbol", "")))
        elif tool_name == "get_positions":
            result = await loop.run_in_executor(None, bridge.get_positions)
        elif tool_name == "open_position":
            result = await loop.run_in_executor(None, lambda: bridge.open_position(
                symbol=params.get("symbol", ""),
                volume=params.get("volume", 0.01),
                position_type=params.get("type", "BUY"),
                stop_loss=params.get("sl", 0.0),
                take_profit=params.get("tp", 0.0),
                magic=params.get("magic", 123456),
                comment=params.get("comment", "Dutchkem AI"),
            ))
        elif tool_name == "close_position":
            result = await loop.run_in_executor(None, lambda: bridge.close_position(params.get("ticket", 0)))
        elif tool_name == "modify_position":
            result = await loop.run_in_executor(None, lambda: bridge.modify_position(
                ticket=params.get("ticket", 0),
                stop_loss=params.get("sl", 0.0),
                take_profit=params.get("tp", 0.0),
            ))
        elif tool_name == "get_trade_history":
            result = await loop.run_in_executor(None, lambda: bridge.get_trade_history(params.get("days", 30)))
        elif tool_name == "get_performance_stats":
            result = await loop.run_in_executor(None, lambda: bridge.get_trade_history(30))
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error("Tool %s failed: %s", tool_name, e)
        result = {"error": str(e)}

    return web.json_response({"result": result})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_post("/connect", handle_connect)
    app.router.add_post("/disconnect", handle_disconnect)
    app.router.add_get("/tools/{tool_name}", handle_tool)
    app.router.add_post("/tools/{tool_name}", handle_tool)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    bridge_port = int(os.environ.get("MCP_BRIDGE_PORT", 8082))
    logger.info("Starting Native MCP Bridge on port %d...", bridge_port)
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=bridge_port)
