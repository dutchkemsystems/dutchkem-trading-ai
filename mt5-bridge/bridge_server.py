"""
DUTCHKEM MT5 BRIDGE — Lightweight Python HTTP Server
Replaces Docker-based SYNX-MT5-MCP bridge.
Exposes MT5 operations via REST API on port 8082.
"""

import json
import logging
import sys
import time
import traceback
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("mt5-bridge")

# ── MT5 Connection ──────────────────────────────────────────────────

MT5_CONNECTED = False
MT5_LOGIN = None
MT5_PASSWORD = None
MT5_SERVER = None


def mt5_connect(login=None, password=None, server=None):
    """Initialize MT5 connection."""
    global MT5_CONNECTED, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

    import MetaTrader5 as mt5

    if login:
        MT5_LOGIN = login
    if password:
        MT5_PASSWORD = password
    if server:
        MT5_SERVER = server

    kwargs = {}
    if MT5_LOGIN:
        kwargs["login"] = int(MT5_LOGIN)
    if MT5_PASSWORD:
        kwargs["password"] = MT5_PASSWORD
    if MT5_SERVER:
        kwargs["server"] = MT5_SERVER

    if not mt5.initialize(**kwargs):
        error = mt5.last_error()
        logger.error("MT5 init failed: %s", error)
        return {"success": False, "error": str(error)}

    MT5_CONNECTED = True
    account = mt5.account_info()
    logger.info("MT5 connected: account=%s server=%s", account.login if account else "N/A", MT5_SERVER)
    return {
        "success": True,
        "status": "connected",
        "account": account.login if account else None,
        "server": MT5_SERVER,
    }


def mt5_disconnect():
    """Shutdown MT5 connection."""
    global MT5_CONNECTED
    import MetaTrader5 as mt5
    mt5.shutdown()
    MT5_CONNECTED = False
    return {"success": True, "status": "disconnected"}


# ── MT5 Operations ──────────────────────────────────────────────────


def get_account_info():
    """Get MT5 account information."""
    import MetaTrader5 as mt5
    info = mt5.account_info()
    if info:
        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "margin_level": info.margin_level,
            "profit": info.profit,
            "leverage": info.leverage,
            "currency": info.currency,
            "login": info.login,
            "server": info.server,
            "name": info.name,
        }
    return {"error": str(mt5.last_error())}


def get_positions():
    """Get all open positions."""
    import MetaTrader5 as mt5
    positions = mt5.positions_get()
    if positions is None:
        return []
    return [
        {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume,
            "price_open": p.price_open,
            "price_current": p.price_current,
            "sl": p.sl,
            "tp": p.tp,
            "profit": p.profit,
            "swap": p.swap,
            "time": p.time,
            "magic": p.magic,
            "comment": p.comment,
        }
        for p in positions
    ]


def get_orders():
    """Get all pending orders."""
    import MetaTrader5 as mt5
    orders = mt5.orders_get()
    if orders is None:
        return []
    return [
        {
            "ticket": o.ticket,
            "symbol": o.symbol,
            "type": o.type,
            "volume": o.volume_current,
            "price": o.price_open,
            "sl": o.sl,
            "tp": o.tp,
            "expiration": o.time_expiration,
            "magic": o.magic,
            "comment": o.comment,
        }
        for o in orders
    ]


def get_symbols():
    """Get all available symbols."""
    import MetaTrader5 as mt5
    symbols = mt5.symbols_get()
    if symbols is None:
        return []
    return [
        {
            "name": s.name,
            "bid": s.bid,
            "ask": s.ask,
            "spread": s.spread,
            "volume": s.volume_real,
            "point": s.point,
            "digits": s.digits,
            "trade_contract_size": s.trade_contract_size,
            "visible": s.visible,
        }
        for s in symbols
        if s.visible
    ]


def get_candles(symbol, timeframe, count):
    """Get candle data."""
    import MetaTrader5 as mt5

    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None:
        return []
    return [
        {
            "time": int(r["time"]),
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r["tick_volume"],
        }
        for r in rates
    ]


def open_position(symbol, volume, position_type, stop_loss=0, take_profit=0, magic=123456, comment="V6.5"):
    """Open a new position."""
    import MetaTrader5 as mt5

    order_type = mt5.ORDER_TYPE_BUY if position_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": price,
        "sl": float(stop_loss),
        "tp": float(take_profit),
        "magic": int(magic),
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None:
        return {"success": False, "error": str(mt5.last_error())}
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {"success": False, "error": result.comment, "retcode": result.retcode}
    return {
        "success": True,
        "ticket": result.order,
        "price": result.price,
        "volume": result.volume,
    }


def close_position(ticket):
    """Close a position by ticket."""
    import MetaTrader5 as mt5

    position = mt5.positions_get(ticket=ticket)
    if not position:
        return {"success": False, "error": "Position not found"}
    position = position[0]

    close_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
    price = mt5.symbol_info_tick(position.symbol).bid if position.type == 0 else mt5.symbol_info_tick(position.symbol).ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": close_type,
        "position": ticket,
        "price": price,
        "magic": 123456,
        "comment": "V6.5-close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None:
        return {"success": False, "error": str(mt5.last_error())}
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {"success": False, "error": result.comment, "retcode": result.retcode}
    return {"success": True, "ticket": result.order}


def modify_position(ticket, stop_loss=None, take_profit=None):
    """Modify SL/TP of an open position."""
    import MetaTrader5 as mt5

    position = mt5.positions_get(ticket=ticket)
    if not position:
        return {"success": False, "error": "Position not found"}
    position = position[0]

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": position.symbol,
        "position": ticket,
        "sl": float(stop_loss) if stop_loss is not None else position.sl,
        "tp": float(take_profit) if take_profit is not None else position.tp,
    }

    result = mt5.order_send(request)
    if result is None:
        return {"success": False, "error": str(mt5.last_error())}
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {"success": False, "error": result.comment, "retcode": result.retcode}
    return {"success": True}


# ── HTTP Server ─────────────────────────────────────────────────────


class MT5BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MT5 bridge API."""

    def log_message(self, format, *args):
        logger.info("%s - %s", self.client_address[0], format % args)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return json.loads(self.rfile.read(length))
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        routes = {
            "": lambda: {"status": "running", "bridge": "dutchkem-mt5-bridge", "version": "1.0.0"},
            "/health": lambda: {"status": "healthy", "mt5_connected": MT5_CONNECTED, "timestamp": datetime.now().isoformat()},
            "/connect": lambda: mt5_connect(),
            "/disconnect": lambda: mt5_disconnect(),
            "/account": lambda: get_account_info(),
            "/positions": lambda: {"positions": get_positions()},
            "/orders": lambda: {"orders": get_orders()},
            "/symbols": lambda: {"symbols": get_symbols()},
        }

        if path in routes:
            try:
                self._send_json(routes[path]())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif path.startswith("/candles/"):
            parts = path.split("/")
            symbol = parts[2] if len(parts) > 2 else "EURUSD"
            tf = params.get("timeframe", ["H1"])[0]
            count = int(params.get("count", ["100"])[0])
            try:
                self._send_json({"candles": get_candles(symbol, tf, count)})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Not found", "path": path}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_body()

        try:
            if path == "/connect":
                result = mt5_connect(
                    login=body.get("login") or body.get("params", {}).get("login"),
                    password=body.get("password") or body.get("params", {}).get("password"),
                    server=body.get("server") or body.get("params", {}).get("server"),
                )
                self._send_json(result)

            elif path == "/disconnect":
                self._send_json(mt5_disconnect())

            elif path == "/open_position":
                self._send_json(open_position(
                    symbol=body.get("symbol", ""),
                    volume=body.get("volume", 0.01),
                    position_type=body.get("position_type", body.get("type", "BUY")),
                    stop_loss=body.get("stop_loss", 0),
                    take_profit=body.get("take_profit", 0),
                    magic=body.get("magic", 123456),
                    comment=body.get("comment", "V6.5"),
                ))

            elif path == "/close_position":
                self._send_json(close_position(ticket=body.get("ticket", 0)))

            elif path == "/modify_position":
                self._send_json(modify_position(
                    ticket=body.get("ticket", 0),
                    stop_loss=body.get("stop_loss"),
                    take_profit=body.get("take_profit"),
                ))

            else:
                self._send_json({"error": "Not found", "path": path}, 404)

        except Exception as e:
            logger.error("POST %s failed: %s", path, traceback.format_exc())
            self._send_json({"error": str(e)}, 500)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082

    # Auto-connect to MT5 on startup
    logger.info("Starting Dutchkem MT5 Bridge on port %d...", port)
    result = mt5_connect(
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER,
    )
    logger.info("MT5 connect result: %s", result)

    server = HTTPServer(("0.0.0.0", port), MT5BridgeHandler)
    logger.info("Bridge listening on http://0.0.0.0:%d", port)
    logger.info("Health check: http://localhost:%d/health", port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down bridge...")
        mt5_disconnect()
        server.server_close()


if __name__ == "__main__":
    main()
