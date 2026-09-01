import logging
from datetime import datetime
from typing import Any

from .influxdb_client import write_candles_batch, write_tick

logger = logging.getLogger("market_data")


class MarketDataIngestion:
    def __init__(self):
        self._buffer: dict[str, list[dict]] = {}
        self._buffer_limit = 100

    def ingest_candle(self, symbol: str, timeframe: str, candle: dict[str, Any]):
        key = f"{symbol}:{timeframe}"
        if key not in self._buffer:
            self._buffer[key] = []

        self._buffer[key].append(candle)

        if len(self._buffer[key]) >= self._buffer_limit:
            self.flush(symbol, timeframe)

    def flush(self, symbol: str | None = None, timeframe: str | None = None):
        if symbol and timeframe:
            key = f"{symbol}:{timeframe}"
            candles = self._buffer.pop(key, [])
            if candles:
                write_candles_batch(symbol, timeframe, candles)
                logger.debug("Flushed %d candles for %s", len(candles), key)
        else:
            for key, candles in list(self._buffer.items()):
                if candles:
                    sym, tf = key.split(":", 1)
                    write_candles_batch(sym, tf, candles)
            self._buffer.clear()

    def ingest_tick(self, symbol: str, tick: dict[str, Any]):
        write_tick(symbol, tick)

    def ingest_ohlcv_from_mt5(self, symbol: str, timeframe: str, data: list[list]):
        for bar in data:
            if len(bar) >= 6:
                candle = {
                    "timestamp": bar[0] if isinstance(bar[0], datetime) else datetime.utcnow(),
                    "open": bar[1],
                    "high": bar[2],
                    "low": bar[3],
                    "close": bar[4],
                    "volume": bar[5],
                }
                self.ingest_candle(symbol, timeframe, candle)

        self.flush(symbol, timeframe)

    def sync_historical(self, symbol: str, timeframe: str, candles: list[dict[str, Any]]):
        batch_size = 500
        for i in range(0, len(candles), batch_size):
            batch = candles[i:i + batch_size]
            write_candles_batch(symbol, timeframe, batch)
            logger.info("Synced batch %d-%d for %s %s", i, i + len(batch), symbol, timeframe)


ingestion = MarketDataIngestion()
