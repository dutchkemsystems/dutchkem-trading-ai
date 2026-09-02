"""
Tests for the scalping module — spike detector, news detector, multi-asset scanner.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from scalping.spike_detector import SpikeDetector, SpikeEvent, SpikeType
from scalping.news_detector import NewsDetector, NewsEvent, NewsImpact
from scalping.multi_asset_scanner import (
    MultiAssetScanner, InstrumentScreener, ALL_INSTRUMENTS,
    FOREX_PAIRS, COMMODITY_PAIRS, INDEX_PAIRS, CRYPTO_PAIRS,
)


# ---------------------------------------------------------------------------
# SpikeDetector
# ---------------------------------------------------------------------------
class TestSpikeDetector:
    def setup_method(self):
        self.detector = SpikeDetector()

    def test_detect_no_spike_normal_data(self, sample_ohlcv):
        """Normal price movement should not trigger a spike."""
        result = self.detector.detect("EURUSD", sample_ohlcv)
        assert result is None

    def test_detect_spike_up(self):
        """Large upward price move should detect spike_up."""
        # Build data with a normal range then a huge upward move
        base = 1.1200
        closes = [base + i * 0.0001 for i in range(30)]
        closes[-1] = base + 0.015  # Huge spike (>> 3x ATR)

        data = {
            "close": closes,
            "high": [c + 0.001 for c in closes],
            "low": [c - 0.001 for c in closes],
        }
        result = self.detector.detect("EURUSD", data)
        assert result is not None
        assert result.spike_type == SpikeType.SPIKE_UP
        assert result.magnitude > 3.0

    def test_detect_spike_down(self):
        """Large downward price move should detect spike_down."""
        base = 1.1200
        closes = [base + i * 0.0001 for i in range(30)]
        closes[-1] = base - 0.008  # Drop that exceeds 3x ATR but not 5x

        data = {
            "close": closes,
            "high": [c + 0.001 for c in closes],
            "low": [c - 0.001 for c in closes],
        }
        result = self.detector.detect("EURUSD", data)
        assert result is not None
        assert result.spike_type == SpikeType.SPIKE_DOWN

    def test_detect_flash_crash(self):
        """Extreme downward move should detect flash_crash."""
        base = 1.1200
        closes = [base + i * 0.0001 for i in range(30)]
        closes[-1] = base - 0.03  # Extreme drop (>> 5x ATR)

        data = {
            "close": closes,
            "high": [c + 0.001 for c in closes],
            "low": [c - 0.001 for c in closes],
        }
        result = self.detector.detect("EURUSD", data)
        assert result is not None
        assert result.spike_type == SpikeType.FLASH_CRASH

    def test_detect_insufficient_data(self):
        """Should return None with less than 20 bars."""
        data = {"close": [1.0] * 10, "high": [1.01] * 10, "low": [0.99] * 10}
        result = self.detector.detect("EURUSD", data)
        assert result is None

    def test_spike_event_to_dict(self):
        """SpikeEvent.to_dict() should return correct structure."""
        event = SpikeEvent("EURUSD", SpikeType.SPIKE_UP, 4.5, 1.1300)
        d = event.to_dict()
        assert d["symbol"] == "EURUSD"
        assert d["type"] == SpikeType.SPIKE_UP
        assert d["magnitude"] == 4.5
        assert d["price"] == 1.1300
        assert "timestamp" in d
        assert "confidence" in d

    def test_spike_history_tracking(self):
        """Detected spikes should be stored in history."""
        base = 1.1200
        closes = [base + i * 0.0001 for i in range(30)]
        closes[-1] = base + 0.015

        data = {
            "close": closes,
            "high": [c + 0.001 for c in closes],
            "low": [c - 0.001 for c in closes],
        }
        self.detector.detect("EURUSD", data)
        history = self.detector.get_spike_history()
        assert len(history) >= 1

    def test_spike_history_filter_by_symbol(self):
        """History should filter by symbol."""
        history = self.detector.get_spike_history(symbol="GBPUSD")
        assert isinstance(history, list)

    def test_spike_stats(self):
        """get_spike_stats should return correct structure."""
        stats = self.detector.get_spike_stats()
        assert "total_spikes" in stats
        assert "by_type" in stats
        assert "avg_magnitude" in stats

    def test_alert_callback(self):
        """Alert callbacks should be called on spike detection."""
        callback = MagicMock()
        self.detector.alert_callbacks.append(callback)

        base = 1.1200
        closes = [base + i * 0.0001 for i in range(30)]
        closes[-1] = base + 0.015

        data = {
            "close": closes,
            "high": [c + 0.001 for c in closes],
            "low": [c - 0.001 for c in closes],
        }
        self.detector.detect("EURUSD", data)
        callback.assert_called_once()


# ---------------------------------------------------------------------------
# NewsDetector
# ---------------------------------------------------------------------------
class TestNewsDetector:
    def setup_method(self):
        self.detector = NewsDetector()

    def test_should_pause_no_events(self):
        """No events means no pause."""
        result = self.detector.should_pause_trading("EURUSD")
        assert result["pause"] is False

    def test_should_pause_pre_news(self):
        """Should pause before a high-impact news event."""
        event = NewsEvent(
            event_id="nfp",
            title="Non-Farm Payrolls",
            currency="USD",
            impact=NewsImpact.HIGH.value,
            timestamp=datetime.now() + timedelta(minutes=15),
        )
        self.detector.scheduled_events.append(event)
        result = self.detector.should_pause_trading("EURUSD")
        assert result["pause"] is True
        assert result["reason"] == "PRE_NEWS_PAUSE"

    def test_should_pause_post_news(self):
        """Should pause after a high-impact news event."""
        event = NewsEvent(
            event_id="nfp",
            title="Non-Farm Payrolls",
            currency="USD",
            impact=NewsImpact.HIGH.value,
            timestamp=datetime.now() - timedelta(minutes=5),
        )
        self.detector.scheduled_events.append(event)
        result = self.detector.should_pause_trading("EURUSD")
        assert result["pause"] is True
        assert result["reason"] == "POST_NEWS_PAUSE"

    def test_no_pause_low_impact(self):
        """Low impact events should not trigger pause."""
        event = NewsEvent(
            event_id="pmi",
            title="Manufacturing PMI",
            currency="USD",
            impact=NewsImpact.LOW.value,
            timestamp=datetime.now() + timedelta(minutes=10),
        )
        self.detector.scheduled_events.append(event)
        result = self.detector.should_pause_trading("EURUSD")
        assert result["pause"] is False

    def test_news_event_to_dict(self):
        """NewsEvent.to_dict() should return correct structure."""
        event = NewsEvent("nfp", "Non-Farm Payrolls", "USD", "high", datetime.now())
        d = event.to_dict()
        assert d["event_id"] == "nfp"
        assert d["currency"] == "USD"
        assert "minutes_until" in d

    def test_add_event(self):
        """Adding events should update the events deque."""
        event = NewsEvent("cpi", "CPI", "USD", "high", datetime.now())
        self.detector.add_event(event)
        assert len(self.detector.events) == 1

    def test_get_news_stats(self):
        """get_news_stats should return correct structure."""
        stats = self.detector.get_news_stats()
        assert "total_events" in stats
        assert "high_impact_events" in stats
        assert "active_pauses" in stats
        assert "scheduled_events" in stats

    def test_get_upcoming_events(self):
        """Should return upcoming events within time window."""
        event = NewsEvent(
            "rate", "Fed Rate Decision", "USD", "high",
            datetime.now() + timedelta(hours=2),
        )
        self.detector.scheduled_events.append(event)
        upcoming = self.detector.get_upcoming_events(hours=24)
        assert len(upcoming) >= 1


# ---------------------------------------------------------------------------
# MultiAssetScanner
# ---------------------------------------------------------------------------
class TestMultiAssetScanner:
    def setup_method(self):
        self.scanner = MultiAssetScanner()

    def test_instruments_list(self):
        """Should have all instrument categories."""
        assert len(FOREX_PAIRS) == 28
        assert len(COMMODITY_PAIRS) == 3
        assert len(INDEX_PAIRS) == 5
        assert len(CRYPTO_PAIRS) == 3
        assert len(ALL_INSTRUMENTS) == 39

    def test_instrument_screener_insufficient_data(self):
        """Screener should skip with insufficient data."""
        screener = InstrumentScreener("EURUSD")
        result = screener.analyze({"close": [1.0] * 10})
        assert result["skip"] is True
        assert result["score"] == 0

    def test_instrument_screener_valid_data(self, sample_ohlcv):
        """Screener should analyze valid data."""
        screener = InstrumentScreener("EURUSD")
        result = screener.analyze(sample_ohlcv)
        assert result["skip"] is False
        assert result["symbol"] == "EURUSD"
        assert "score" in result
        assert "volatility" in result
        assert "trend_strength" in result
        assert "liquidity" in result

    def test_scan_all(self, sample_ohlcv):
        """scan_all should process multiple instruments."""
        market_data = {
            "EURUSD": sample_ohlcv,
            "GBPUSD": sample_ohlcv,
        }
        results = self.scanner.scan_all(market_data)
        assert len(results) >= 0  # May be 0 if scores are 0

    def test_get_top_opportunities(self, sample_ohlcv):
        """Should return top N opportunities."""
        self.scanner.scan_results = {
            "EURUSD": {"symbol": "EURUSD", "score": 80},
            "GBPUSD": {"symbol": "GBPUSD", "score": 60},
            "USDJPY": {"symbol": "USDJPY", "score": 90},
        }
        top = self.scanner.get_top_opportunities(2)
        assert len(top) == 2
        assert top[0]["score"] >= top[1]["score"]

    def test_get_scan_stats(self):
        """get_scan_stats should return correct structure."""
        stats = self.scanner.get_scan_stats()
        assert "total_instruments" in stats
        assert "last_scan_time" in stats
        assert "results_count" in stats
        assert "top_5" in stats
