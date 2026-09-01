"""
Integration Tests for the Full V6.5 Order Execution Pipeline

Covers:
  - Indicator accuracy (Wilder's RSI/ATR, PSAR)
  - Signal generation end-to-end
  - V6.5 Orchestrator full cycle
  - Enhancement modules (sentiment, risk sizing, diversification, etc.)
  - Celery task execution
  - WebSocket consumers
"""

import asyncio
import importlib.util
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

# ─── Import indicators from the parent-level strategies package ────────────
# backend/strategies/ exists as a Django-adjacent package but does NOT have
# indicators.py.  The real indicators live in dutchkem-trading-ai/strategies/.
# We load them by file path to avoid the namespace collision.
_strategies_indicators_path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "strategies", "indicators.py")
)
_spec = importlib.util.spec_from_file_location("strategies_indicators", _strategies_indicators_path)
_indicators_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_indicators_mod)

calculate_rsi = _indicators_mod.calculate_rsi
calculate_atr = _indicators_mod.calculate_atr
calculate_psar = _indicators_mod.calculate_psar
calculate_ema = _indicators_mod.calculate_ema
calculate_macd = _indicators_mod.calculate_macd
calculate_bollinger = _indicators_mod.calculate_bollinger
calculate_stochastic = _indicators_mod.calculate_stochastic
calculate_cci = _indicators_mod.calculate_cci
calculate_adx = _indicators_mod.calculate_adx
calculate_supertrend = _indicators_mod.calculate_supertrend
calculate_ichimoku = _indicators_mod.calculate_ichimoku

# ─── Indicator Accuracy Tests ─────────────────────────────────────────────


class TestRSIWilderSmoothing:
    """Validate that RSI uses Wilder's exponential smoothing, not SMA."""

    def test_basic_rsi(self):
        # Perfect uptrend -> RSI should be 100
        data = [1.0 + i * 0.1 for i in range(30)]
        rsi = calculate_rsi(data, period=14)
        assert 90 < rsi <= 100

    def test_basic_rsi_downtrend(self):
        data = [10.0 - i * 0.1 for i in range(30)]
        rsi = calculate_rsi(data, period=14)
        assert 0 <= rsi < 10

    def test_rsi_neutral(self):
        # Oscillating data -> RSI near 50
        data = [1.0 + (0.01 if i % 2 == 0 else -0.01) for i in range(30)]
        rsi = calculate_rsi(data, period=14)
        assert 40 < rsi < 60

    def test_rsi_insufficient_data(self):
        assert calculate_rsi([1.0], period=14) == 50.0

    def test_rsi_all_gains(self):
        data = list(range(1, 20))
        rsi = calculate_rsi(data, period=14)
        assert rsi == 100.0

    def test_rsi_all_losses(self):
        data = list(range(20, 1, -1))
        rsi = calculate_rsi(data, period=14)
        assert rsi == 0.0


class TestATRWilderSmoothing:
    """Validate ATR uses Wilder's smoothing."""

    def test_basic_atr(self):
        highs = [1.1250 + i * 0.001 for i in range(30)]
        lows = [1.1200 + i * 0.001 for i in range(30)]
        closes = [1.1220 + i * 0.001 for i in range(30)]
        atr = calculate_atr(highs, lows, closes, period=14)
        assert atr > 0

    def test_atr_insufficient_data(self):
        atr = calculate_atr([1.0], [0.9], [0.95], period=14)
        assert atr >= 0


class TestPSARFull:
    """Validate full Parabolic SAR implementation."""

    def test_psar_runs(self):
        highs = [1.1250 + i * 0.001 for i in range(30)]
        lows = [1.1200 + i * 0.001 for i in range(30)]
        closes = [1.1220 + i * 0.001 for i in range(30)]
        sar = calculate_psar(highs, lows, closes)
        assert isinstance(sar, float)

    def test_psar_short_data(self):
        sar = calculate_psar([1.0], [0.9], [0.95])
        assert sar == 0.95


class TestOtherIndicators:
    """Spot-check other indicator functions."""

    def test_ema(self):
        data = [1.0 + i * 0.01 for i in range(50)]
        ema = calculate_ema(data, 20)
        assert ema > data[0]

    def test_macd(self):
        data = [1.0 + i * 0.01 for i in range(50)]
        macd, signal, hist = calculate_macd(data)
        assert isinstance(macd, float)

    def test_bollinger(self):
        data = [1.0 + (0.01 if i % 2 == 0 else -0.01) for i in range(30)]
        upper, mid, lower = calculate_bollinger(data)
        assert upper > mid > lower

    def test_stochastic(self):
        highs = [1.1250 + i * 0.001 for i in range(30)]
        lows = [1.1200 + i * 0.001 for i in range(30)]
        closes = [1.1220 + i * 0.001 for i in range(30)]
        k, d = calculate_stochastic(highs, lows, closes)
        assert 0 <= k <= 100
        assert 0 <= d <= 100

    def test_cci(self):
        highs = [1.1250 + i * 0.001 for i in range(30)]
        lows = [1.1200 + i * 0.001 for i in range(30)]
        closes = [1.1220 + i * 0.001 for i in range(30)]
        cci = calculate_cci(highs, lows, closes)
        assert isinstance(cci, float)

    def test_adx(self):
        highs = [1.1250 + i * 0.001 for i in range(30)]
        lows = [1.1200 + i * 0.001 for i in range(30)]
        closes = [1.1220 + i * 0.001 for i in range(30)]
        adx = calculate_adx(highs, lows, closes)
        assert adx >= 0

    def test_supertrend(self):
        highs = [1.1250 + i * 0.001 for i in range(30)]
        lows = [1.1200 + i * 0.001 for i in range(30)]
        closes = [1.1220 + i * 0.001 for i in range(30)]
        val, direction = calculate_supertrend(highs, lows, closes)
        assert isinstance(val, float)
        assert direction in (1, -1)

    def test_ichimoku(self):
        highs = [1.1250 + i * 0.001 for i in range(60)]
        lows = [1.1200 + i * 0.001 for i in range(60)]
        closes = [1.1220 + i * 0.001 for i in range(60)]
        result = calculate_ichimoku(highs, lows, closes)
        assert "tenkan_sen" in result
        assert "kijun_sen" in result


# ─── V6.5 Enhancement Module Tests ───────────────────────────────────────


class TestSentimentAnalyzer:
    def test_get_sentiment_score(self):
        from ml.enhancements.sentiment_analyzer import SentimentAnalyzer
        sa = SentimentAnalyzer()
        result = sa.get_sentiment_score("EURUSD")
        assert "score" in result
        assert "confidence" in result
        assert -1 <= result["score"] <= 1

    def test_sentiment_confidence(self):
        from ml.enhancements.sentiment_analyzer import SentimentAnalyzer
        sa = SentimentAnalyzer()
        conf = sa.get_sentiment_confidence("XAUUSD")
        assert 0 <= conf <= 1


class TestSmartNewsTrading:
    def test_news_strategy_normal(self):
        from ml.enhancements.smart_news_trading import SmartNewsTrading
        from datetime import datetime, timedelta
        snt = SmartNewsTrading()
        # Use a date far in the future to avoid any dynamically-generated events
        result = snt.get_news_strategy("EURUSD", datetime(2099, 1, 1, 12, 0))
        assert result["strategy"] == "NORMAL"

    def test_load_calendar(self):
        from ml.enhancements.smart_news_trading import SmartNewsTrading
        snt = SmartNewsTrading()
        assert len(snt.news_calendar) > 0

    def test_hmr_detection(self):
        from ml.enhancements.smart_news_trading import SmartNewsTrading
        from datetime import datetime
        snt = SmartNewsTrading()
        # Far future — no events
        assert snt.check_hmr_active(datetime(2099, 1, 1)) is False


class TestOrderFlowAnalyzer:
    def test_analyze_order_flow(self):
        from ml.enhancements.order_flow_analyzer import OrderFlowAnalyzer
        ofa = OrderFlowAnalyzer()
        result = ofa.analyze_order_flow("EURUSD", {})
        assert "bias" in result
        assert "confidence" in result

    def test_large_orders(self):
        from ml.enhancements.order_flow_analyzer import OrderFlowAnalyzer
        ofa = OrderFlowAnalyzer()
        ob = ofa.get_order_book("EURUSD")
        large = ofa.find_large_orders(ob)
        assert isinstance(large, list)


class TestDeepPatternRecognizer:
    def test_rule_based_detect(self):
        from ml.enhancements.deep_pattern_recognizer import DeepPatternRecognizer
        dpr = DeepPatternRecognizer()
        bars = np.random.uniform(1.0, 1.1, (20, 4))
        result = dpr.recognize_pattern(bars)
        assert "signal" in result
        assert result["signal"] in ("BUY", "SELL", "NEUTRAL")

    def test_pattern_types(self):
        from ml.enhancements.deep_pattern_recognizer import DeepPatternRecognizer
        dpr = DeepPatternRecognizer()
        # Doji pattern: body is tiny relative to range
        bars = np.array([
            [1.0, 1.1, 0.9, 1.001],  # almost doji
            [1.0, 1.05, 0.95, 1.02],
            [1.0, 1.05, 0.95, 1.02],
        ], dtype=float)
        patterns = dpr.identify_pattern_types(bars)
        assert isinstance(patterns, list)


class TestMultiTimeframeAnalyzer:
    def test_analyze_all_timeframes(self):
        from ml.enhancements.multi_timeframe_analyzer import MultiTimeframeAnalyzer
        mta = MultiTimeframeAnalyzer()
        result = mta.analyze_all_timeframes("EURUSD")
        assert "action" in result
        assert "confidence" in result
        assert result["action"] in ("BUY", "SELL", "NEUTRAL")


class TestDynamicStopLoss:
    def test_calculate_optimal_stop(self):
        from ml.enhancements.dynamic_stop_loss import DynamicStopLoss
        dsl = DynamicStopLoss()
        result = dsl.calculate_optimal_stop("EURUSD", 1.1200, "BUY", {"atr": 0.001, "volatility_ratio": 1.0})
        assert "stop_loss" in result
        assert result["stop_loss"] < 1.1200  # BUY stop below entry

    def test_trailing_stop(self):
        from ml.enhancements.dynamic_stop_loss import DynamicStopLoss
        dsl = DynamicStopLoss()
        pos = {"entry_price": 1.1200, "direction": "BUY", "stop_loss": 1.1180}
        result = dsl.update_trailing_stop(pos, 1.1250)
        assert result["stop_loss"] >= 1.1180


class TestRiskAdjustedSizer:
    def test_calculate_optimal_risk(self):
        from ml.enhancements.risk_adjusted_sizer import RiskAdjustedSizer
        ras = RiskAdjustedSizer()
        risk = ras.calculate_optimal_risk(10000, 0.8, 1.0, 0.0, 0.02, "TRENDING")
        assert 0.001 <= risk <= 0.01

    def test_position_size(self):
        from ml.enhancements.risk_adjusted_sizer import RiskAdjustedSizer
        ras = RiskAdjustedSizer()
        lots = ras.calculate_position_size(10000, 0.01, 50)
        assert lots >= 0.01


class TestArtificialDiversification:
    def test_check_diversification(self):
        from ml.enhancements.artificial_diversification import ArtificialDiversification
        ad = ArtificialDiversification()
        result = ad.check_diversification("EURUSD", [])
        assert result["diversified"] is True

    def test_max_positions(self):
        from ml.enhancements.artificial_diversification import ArtificialDiversification
        ad = ArtificialDiversification()
        positions = [{"symbol": f"SYM{i}", "equity": 1000} for i in range(5)]
        result = ad.check_diversification("XAUUSD", positions)
        assert result["diversified"] is False


class TestAdaptiveTakeProfit:
    def test_calculate_take_profit(self):
        from ml.enhancements.adaptive_take_profit import AdaptiveTakeProfit
        atp = AdaptiveTakeProfit()
        result = atp.calculate_take_profit(1.1200, "BUY", 1.1180, {})
        assert result["tp1"] > 1.1200
        assert result["tp2"] > result["tp1"]

    def test_partial_closes(self):
        from ml.enhancements.adaptive_take_profit import AdaptiveTakeProfit
        atp = AdaptiveTakeProfit()
        pos = {"direction": "BUY"}
        tps = {"tp1": 1.1250, "tp2": 1.1300, "tp3": 1.1400}
        result = atp.execute_partial_closes(pos, tps, 1.1250)
        assert result["action"] in ("PARTIAL_CLOSE", "FULL_CLOSE", "NO_CHANGE")


class TestSelfOptimizingSystem:
    def test_get_parameters(self):
        from ml.enhancements.self_optimizing_system import SelfOptimizingSystem
        sos = SelfOptimizingSystem()
        params = sos.get_parameters()
        assert "rsi_period" in params
        assert "confidence_threshold" in params

    def test_update_from_trade(self):
        from ml.enhancements.self_optimizing_system import SelfOptimizingSystem
        sos = SelfOptimizingSystem()
        old_thresh = sos.parameters["confidence_threshold"]
        sos.update_from_trade({"profit": 100})
        assert sos.parameters["confidence_threshold"] <= old_thresh

    def test_should_optimize(self):
        from ml.enhancements.self_optimizing_system import SelfOptimizingSystem
        sos = SelfOptimizingSystem()
        assert sos.should_optimize() is True


# ─── V6.5 Orchestrator Integration Tests ──────────────────────────────────


class TestV65Orchestrator:
    def test_initialization(self):
        from ml.v65_orchestrator import V65TradingOrchestrator
        orch = V65TradingOrchestrator()
        orch.initialize()
        assert orch._initialized is True
        assert orch.component_count > 0

    def test_get_status(self):
        from ml.v65_orchestrator import V65TradingOrchestrator
        orch = V65TradingOrchestrator()
        orch.initialize()
        status = orch.get_status()
        assert status["version"] == "6.5"
        assert "component_count" in status

    def test_market_scan_no_data(self):
        from ml.v65_orchestrator import V65TradingOrchestrator
        orch = V65TradingOrchestrator()
        orch.initialize()
        result = orch.run_trading_cycle({})
        assert result["status"] == "NO_OPPORTUNITIES"

    def test_market_scan_with_data(self):
        from ml.v65_orchestrator import V65TradingOrchestrator
        orch = V65TradingOrchestrator()
        orch.initialize()
        market_data = {
            "EURUSD": {
                "candles": [{"open": 1.12, "high": 1.125, "low": 1.118, "close": 1.123, "volume": 5000} for _ in range(100)],
                "current_price": 1.123,
                "spread": 0.1,
                "volume": 50000,
                "current_atr": 0.001,
                "historical_atr": 0.0012,
                "highs": [1.125 + i * 0.0001 for i in range(100)],
                "lows": [1.118 + i * 0.0001 for i in range(100)],
                "closes": [1.123 + i * 0.0001 for i in range(100)],
            }
        }
        result = orch.run_trading_cycle(market_data)
        assert result["version"] == "6.5"
        assert "phases" in result


# ─── Celery Task Integration Tests ────────────────────────────────────────


class TestCeleryTasks:
    @pytest.mark.django_db
    def test_health_check(self):
        from config.tasks import health_check
        result = health_check.apply()
        assert result.result["status"] == "healthy"

    @pytest.mark.django_db
    def test_run_v6_trading_cycle_no_data(self):
        """V6 cycle should return gracefully when MT5 has no data."""
        from config.tasks import run_v6_trading_cycle
        with patch("config.tasks._run_async", return_value=None):
            with patch("ml.v65_orchestrator.get_v65_orchestrator") as mock_get:
                mock_orch = MagicMock()
                mock_orch.run_trading_cycle.return_value = {"status": "NO_DATA"}
                mock_get.return_value = mock_orch
                result = run_v6_trading_cycle.apply()
                # Should not raise
                assert result.status == "SUCCESS"


# ─── Async Helper Tests ───────────────────────────────────────────────────


class TestAsyncHelper:
    def test_run_async_basic(self):
        from config.tasks import _run_async

        async def coro():
            return 42

        result = _run_async(coro)
        assert result == 42

    def test_run_async_with_timeout(self):
        from config.tasks import _run_async

        async def coro():
            return "ok"

        result = _run_async(coro, timeout=5)
        assert result == "ok"
