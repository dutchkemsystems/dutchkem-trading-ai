# Logging Filters

import logging
from contextvars import ContextVar

# Context variables for request and trading context
current_request: ContextVar[dict] = ContextVar("current_request", default={})
current_trading: ContextVar[dict] = ContextVar("current_trading", default={})


class RequestContextFilter(logging.Filter):
    """Adds request context to log records."""

    def filter(self, record):
        request_data = current_request.get({})
        record.request_id = request_data.get("request_id", "N/A")
        record.user_id = request_data.get("user_id", "N/A")
        record.ip_address = request_data.get("ip_address", "N/A")
        record.method = request_data.get("method", "N/A")
        record.path = request_data.get("path", "N/A")
        record.status_code = request_data.get("status_code", "N/A")
        record.response_time = request_data.get("response_time", "N/A")
        return True


class TradingContextFilter(logging.Filter):
    """Adds trading context to log records."""

    def filter(self, record):
        trading_data = current_trading.get({})
        record.symbol = trading_data.get("symbol", "N/A")
        record.timeframe = trading_data.get("timeframe", "N/A")
        record.position_type = trading_data.get("position_type", "N/A")
        record.volume = trading_data.get("volume", "N/A")
        record.entry_price = trading_data.get("entry_price", "N/A")
        record.stop_loss = trading_data.get("stop_loss", "N/A")
        record.take_profit = trading_data.get("take_profit", "N/A")
        record.signal_type = trading_data.get("signal_type", "N/A")
        record.signal_strength = trading_data.get("signal_strength", "N/A")
        return True


def set_request_context(request_id, user_id, ip_address, method, path, status_code=None, response_time=None):
    """Set request context for logging."""
    current_request.set(
        {
            "request_id": request_id,
            "user_id": user_id,
            "ip_address": ip_address,
            "method": method,
            "path": path,
            "status_code": status_code,
            "response_time": response_time,
        }
    )


def set_trading_context(
    symbol=None,
    timeframe=None,
    position_type=None,
    volume=None,
    entry_price=None,
    stop_loss=None,
    take_profit=None,
    signal_type=None,
    signal_strength=None,
):
    """Set trading context for logging."""
    current_trading.set(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "position_type": position_type,
            "volume": volume,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "signal_type": signal_type,
            "signal_strength": signal_strength,
        }
    )


def clear_trading_context():
    """Clear trading context."""
    current_trading.set({})
