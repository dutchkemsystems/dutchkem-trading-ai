import logging
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

from django.conf import settings

logger = logging.getLogger("market_data")

_client = None
_write_api = None
_query_api = None

WRITE_OPTIONS = None
QUERY_CACHE = {}
QUERY_CACHE_TTL = 30


def _get_write_options():
    global WRITE_OPTIONS
    if WRITE_OPTIONS is None:
        try:
            from influxdb_client.client.write_api import SYNCHRONOUS, WriteOptions
            WRITE_OPTIONS = WriteOptions(
                batch_size=500,
                flush_interval=1_000,
                jitter_interval=200,
                retry_interval=5_000,
                max_retries=5,
                max_retry_delay=30_000,
                exponential_base=2,
            )
        except ImportError:
            return SYNCHRONOUS
    return WRITE_OPTIONS


def get_influxdb_client():
    global _client
    if _client is None:
        try:
            from influxdb_client import InfluxDBClient
            _client = InfluxDBClient(
                url=settings.INFLUXDB_URL,
                token=settings.INFLUXDB_TOKEN,
                org=settings.INFLUXDB_ORG,
                timeout=30_000,
                retries=3,
            )
        except ImportError:
            logger.warning("influxdb-client not installed")
            return None
    return _client


def get_write_api():
    global _write_api
    if _write_api is None:
        client = get_influxdb_client()
        if client:
            _write_api = client.write_api(write_options=_get_write_options())
    return _write_api


def get_query_api():
    global _query_api
    if _query_api is None:
        client = get_influxdb_client()
        if client:
            _query_api = client.query_api()
    return _query_api


def health_check():
    client = get_influxdb_client()
    if not client:
        return False
    try:
        ready = client.ping()
        return ready
    except Exception as e:
        logger.error("InfluxDB health check failed: %s", e)
        return False


def ensure_bucket(bucket: str = None):
    bucket = bucket or settings.INFLUXDB_BUCKET
    client = get_influxdb_client()
    if not client:
        return False
    try:
        buckets_api = client.buckets_api()
        org = settings.INFLUXDB_ORG
        existing = buckets_api.find_bucket_by_name(bucket)
        if not existing:
            buckets_api.create_bucket(
                bucket_name=bucket,
                org=org,
                retention_rules=[{"type": "expire", "everySeconds": 90 * 24 * 3600}],
            )
            logger.info("Created InfluxDB bucket: %s", bucket)
        return True
    except Exception as e:
        logger.error("Failed to ensure bucket %s: %s", bucket, e)
        return False


def write_point(measurement: str, tags: dict[str, str], fields: dict[str, Any], timestamp: datetime = None):
    from influxdb_client import Point

    write_api = get_write_api()
    if not write_api:
        return False

    point = Point(measurement)
    for k, v in tags.items():
        point = point.tag(k, v)
    for k, v in fields.items():
        point = point.field(k, v)
    if timestamp:
        point = point.time(timestamp)

    try:
        write_api.write(bucket=settings.INFLUXDB_BUCKET, record=point)
        return True
    except Exception as e:
        logger.error("Failed to write point: %s", e)
        return False


def write_points_batch(points: list[dict[str, Any]]):
    from influxdb_client import Point

    write_api = get_write_api()
    if not write_api or not points:
        return False

    records = []
    for p in points:
        point = Point(p.get("measurement", "unknown"))
        for k, v in p.get("tags", {}).items():
            point = point.tag(k, v)
        for k, v in p.get("fields", {}).items():
            point = point.field(k, v)
        if "timestamp" in p:
            point = point.time(p["timestamp"])
        records.append(point)

    try:
        write_api.write(bucket=settings.INFLUXDB_BUCKET, record=records)
        logger.info("Wrote batch of %d points", len(records))
        return True
    except Exception as e:
        logger.error("Failed to write batch: %s", e)
        return False


def write_candle(symbol: str, timeframe: str, candle: dict[str, Any]):
    return write_point(
        measurement="ohlcv",
        tags={"symbol": symbol, "timeframe": timeframe},
        fields={
            "open": float(candle["open"]),
            "high": float(candle["high"]),
            "low": float(candle["low"]),
            "close": float(candle["close"]),
            "volume": float(candle.get("volume", 0)),
        },
        timestamp=candle.get("timestamp", datetime.utcnow()),
    )


def write_candles_batch(symbol: str, timeframe: str, candles: list[dict[str, Any]]):
    points = []
    for candle in candles:
        points.append({
            "measurement": "ohlcv",
            "tags": {"symbol": symbol, "timeframe": timeframe},
            "fields": {
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
                "volume": float(candle.get("volume", 0)),
            },
            "timestamp": candle.get("timestamp", datetime.utcnow()),
        })
    return write_points_batch(points)


def write_tick(symbol: str, tick: dict[str, Any]):
    return write_point(
        measurement="tick",
        tags={"symbol": symbol},
        fields={
            "bid": float(tick.get("bid", 0)),
            "ask": float(tick.get("ask", 0)),
            "spread": float(tick.get("spread", 0)),
        },
        timestamp=tick.get("timestamp", datetime.utcnow()),
    )


def write_indicator(symbol: str, indicator_name: str, value: float, signal: str = None):
    fields = {"value": value}
    if signal:
        fields["signal"] = signal
    return write_point(
        measurement="indicator",
        tags={"symbol": symbol, "indicator": indicator_name},
        fields=fields,
        timestamp=datetime.utcnow(),
    )


def query_raw(flux: str, use_cache: bool = False):
    if use_cache:
        cache_key = hash(flux)
        cached = QUERY_CACHE.get(cache_key)
        if cached and time.time() - cached["time"] < QUERY_CACHE_TTL:
            return cached["data"]

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
                    "measurement": record.get_measurement(),
                    **record.values,
                })
        if use_cache:
            QUERY_CACHE[hash(flux)] = {"data": results, "time": time.time()}
        return results
    except Exception as e:
        logger.error("Query failed: %s", e)
        return []


def query_latest_price(symbol: str):
    flux = f'''
    from(bucket: "{settings.INFLUXDB_BUCKET}")
    |> range(start: -1h)
    |> filter(fn: (r) => r["_measurement"] == "tick")
    |> filter(fn: (r) => r["symbol"] == "{symbol}")
    |> last()
    '''
    results = query_raw(flux)
    if results:
        return {
            "symbol": symbol,
            "bid": results[0].get("bid"),
            "ask": results[0].get("ask"),
            "spread": results[0].get("spread"),
            "time": results[0].get("time"),
        }
    return None


def query_candles(symbol: str, timeframe: str, count: int = 100):
    tf_map = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m", "H1": "1h", "H4": "4h", "D1": "1d"}
    interval = tf_map.get(timeframe, "1h")

    flux = f'''
    from(bucket: "{settings.INFLUXDB_BUCKET}")
    |> range(start: -{count * 60}s)
    |> filter(fn: (r) => r["_measurement"] == "ohlcv")
    |> filter(fn: (r) => r["symbol"] == "{symbol}")
    |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
    |> aggregateWindow(every: {interval}, fn: last, createEmpty: false)
    |> yield(name: "candles")
    '''
    return query_raw(flux)


def query_aggregate(symbol: str, measurement: str, field: str, agg: str = "mean", hours: int = 24):
    flux = f'''
    from(bucket: "{settings.INFLUXDB_BUCKET}")
    |> range(start: -{hours}h)
    |> filter(fn: (r) => r["_measurement"] == "{measurement}")
    |> filter(fn: (r) => r["symbol"] == "{symbol}")
    |> filter(fn: (r) => r["_field"] == "{field}")
    |> aggregateWindow(every: 1h, fn: {agg}, createEmpty: false)
    |> yield(name: "{agg}_{field}")
    '''
    return query_raw(flux)


def close_client():
    global _client, _write_api, _query_api
    if _client:
        _client.close()
        _client = None
        _write_api = None
        _query_api = None
