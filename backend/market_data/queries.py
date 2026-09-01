import logging
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings

from .influxdb_client import get_query_api

logger = logging.getLogger("market_data")


def _build_query(flux: str) -> list[dict]:
    query_api = get_query_api()
    if not query_api:
        return []

    try:
        tables = query_api.query(flux, org=settings.INFLUXDB_ORG)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time": record.get_time(),
                    "symbol": record.values.get("symbol", ""),
                    "timeframe": record.values.get("timeframe", ""),
                    **{k: v for k, v in record.values.items()
                       if k not in ("_time", "_measurement", "result", "table", "symbol", "timeframe")},
                })
        return results
    except Exception as exc:
        logger.error("InfluxDB query failed: %s", exc)
        return []


def get_candles(
    symbol: str,
    timeframe: str = "H1",
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 500,
) -> list[dict]:
    if not start:
        start = datetime.utcnow() - timedelta(days=30)
    if not end:
        end = datetime.utcnow()

    flux = f'''
    from(bucket: "{settings.INFLUXDB_BUCKET}")
      |> range(start: {start.isoformat()}Z, stop: {end.isoformat()}Z)
      |> filter(fn: (r) => r._measurement == "ohlcv")
      |> filter(fn: (r) => r.symbol == "{symbol}")
      |> filter(fn: (r) => r.timeframe == "{timeframe}")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
      |> limit(n: {limit})
    '''
    return _build_query(flux)


def get_latest_price(symbol: str) -> dict | None:
    flux = f'''
    from(bucket: "{settings.INFLUXDB_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "tick")
      |> filter(fn: (r) => r.symbol == "{symbol}")
      |> last()
    '''
    results = _build_query(flux)
    return results[0] if results else None


def get_candle_aggregate(
    symbol: str,
    timeframe: str,
    aggregate_window: str = "1d",
    start: datetime | None = None,
    limit: int = 30,
) -> list[dict]:
    if not start:
        start = datetime.utcnow() - timedelta(days=365)

    flux = f'''
    from(bucket: "{settings.INFLUXDB_BUCKET}")
      |> range(start: {start.isoformat()}Z)
      |> filter(fn: (r) => r._measurement == "ohlcv")
      |> filter(fn: (r) => r.symbol == "{symbol}")
      |> filter(fn: (r) => r.timeframe == "{timeframe}")
      |> aggregateWindow(every: {aggregate_window}, fn: mean, createEmpty: false)
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit})
    '''
    return _build_query(flux)


def get_volume_profile(symbol: str, timeframe: str = "H1", days: int = 30) -> list[dict]:
    start = datetime.utcnow() - timedelta(days=days)

    flux = f'''
    from(bucket: "{settings.INFLUXDB_BUCKET}")
      |> range(start: {start.isoformat()}Z)
      |> filter(fn: (r) => r._measurement == "ohlcv")
      |> filter(fn: (r) => r.symbol == "{symbol}")
      |> filter(fn: (r) => r.timeframe == "{timeframe}")
      |> filter(fn: (r) => r._field == "volume")
      |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)
      |> sort(columns: ["_time"], desc: true)
    '''
    return _build_query(flux)


def get_atr(symbol: str, timeframe: str = "H1", period: int = 14) -> float | None:
    candles = get_candles(symbol, timeframe, limit=period + 1)
    if len(candles) < 2:
        return None

    true_ranges = []
    for i in range(1, len(candles)):
        high = float(candles[i].get("high", 0))
        low = float(candles[i].get("low", 0))
        prev_close = float(candles[i - 1].get("close", 0))
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if not true_ranges:
        return None
    return sum(true_ranges) / len(true_ranges)
