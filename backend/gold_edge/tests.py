"""
Unit tests for the Gold Edge strategy module.

Tests cover:
  - GoldEdgeComposite (GEC)
  - ATRBorderGrid
  - ATRRatioFilter
  - GoldEdgeMatrix (entry logic)
  - GoldEdgeService (pipeline orchestration)
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_ohlcv(n: int = 300, base_price: float = 2000.0) -> pd.DataFrame:
    """Generate synthetic OHLCV for gold-like instruments."""
    np.random.seed(42)
    close = base_price + np.cumsum(np.random.randn(n) * 2.0)
    high = close + np.abs(np.random.randn(n) * 3.0)
    low = close - np.abs(np.random.randn(n) * 3.0)
    open_ = close + np.random.randn(n) * 1.0
    volume = np.random.randint(100, 5000, n)
    ts = pd.date_range("2025-01-01", periods=n, freq="1h")
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "timestamp": ts,
    })


# ===================================================================
# GoldEdgeComposite Tests
# ===================================================================

class TestGoldEdgeComposite:
    """Tests for ge_composite.py"""

    def test_default_weights_sum_to_one(self):
        from gold_edge.ge_composite import GoldEdgeComposite
        gec = GoldEdgeComposite()
        total = (gec.momentum_weight + gec.trend_weight +
                 gec.volatility_weight + gec.dxy_correlation_weight)
        assert abs(total - 1.0) < 0.01

    def test_invalid_weights_raises(self):
        from gold_edge.ge_composite import GoldEdgeComposite
        with pytest.raises(ValueError, match="sum to 1.0"):
            GoldEdgeComposite(momentum_weight=0.5, trend_weight=0.5, volatility_weight=0.5, dxy_correlation_weight=0.5)

    def test_calculate_returns_gec_result(self):
        from gold_edge.ge_composite import GoldEdgeComposite, GECResult
        gec = GoldEdgeComposite()
        df = _make_ohlcv(300)
        result = gec.calculate(df)
        assert isinstance(result, GECResult)
        assert -1 <= result.composite_score <= 1
        assert result.direction in ("LONG", "SHORT", "NEUTRAL")

    def test_calculate_insufficient_data_returns_neutral(self):
        from gold_edge.ge_composite import GoldEdgeComposite, GECResult
        gec = GoldEdgeComposite()
        result = gec.calculate(pd.DataFrame())
        assert result.direction == "NEUTRAL"
        assert result.composite_score == 0.0

    def test_to_dict(self):
        from gold_edge.ge_composite import GoldEdgeComposite
        gec = GoldEdgeComposite()
        df = _make_ohlcv(300)
        result = gec.calculate(df)
        d = result.to_dict()
        assert "composite_score" in d
        assert "momentum_score" in d
        assert "direction" in d
        assert "confidence" in d

    def test_momentum_score_range(self):
        from gold_edge.ge_composite import GoldEdgeComposite
        gec = GoldEdgeComposite()
        df = _make_ohlcv(300)
        score = gec._momentum_score(df)
        assert -1 <= score <= 1

    def test_trend_score_range(self):
        from gold_edge.ge_composite import GoldEdgeComposite
        gec = GoldEdgeComposite()
        df = _make_ohlcv(300)
        score = gec._trend_score(df)
        assert -1 <= score <= 1

    def test_volatility_score_range(self):
        from gold_edge.ge_composite import GoldEdgeComposite
        gec = GoldEdgeComposite()
        df = _make_ohlcv(300)
        score = gec._volatility_score(df)
        assert -1 <= score <= 1

    def test_dxy_score_without_series(self):
        from gold_edge.ge_composite import GoldEdgeComposite
        gec = GoldEdgeComposite()
        df = _make_ohlcv(300)
        score = gec._dxy_correlation_score(df, None)
        assert score == 0.0

    def test_dxy_score_with_series(self):
        from gold_edge.ge_composite import GoldEdgeComposite
        gec = GoldEdgeComposite()
        df = _make_ohlcv(300)
        dxy = pd.Series(np.random.randn(300) * 0.5 + 100)
        score = gec._dxy_correlation_score(df, dxy)
        assert -1 <= score <= 1


# ===================================================================
# ATRBorderGrid Tests
# ===================================================================

class TestATRBorderGrid:
    """Tests for atr_border.py"""

    def test_calculate_returns_border_result(self):
        from gold_edge.atr_border import ATRBorderGrid, ATRBorderResult
        grid = ATRBorderGrid(ema_period=21, atr_period=14)
        df = _make_ohlcv(300)
        result = grid.calculate(df)
        assert isinstance(result, ATRBorderResult)
        assert result.ema_midline > 0
        assert result.atr_value > 0

    def test_borders_has_four_layers(self):
        from gold_edge.atr_border import ATRBorderGrid
        grid = ATRBorderGrid()
        df = _make_ohlcv(300)
        result = grid.calculate(df)
        assert len(result.borders) == 4

    def test_border_layers_ordered(self):
        from gold_edge.atr_border import ATRBorderGrid
        grid = ATRBorderGrid()
        df = _make_ohlcv(300)
        result = grid.calculate(df)
        core = result.borders["core"]
        extended = result.borders["extended"]
        assert core["lower"] > extended["lower"]
        assert core["upper"] < extended["upper"]

    def test_price_position_in_range(self):
        from gold_edge.atr_border import ATRBorderGrid
        grid = ATRBorderGrid()
        df = _make_ohlcv(300)
        result = grid.calculate(df)
        assert 0 <= result.price_position_pct <= 1

    def test_insufficient_data(self):
        from gold_edge.atr_border import ATRBorderGrid, ATRBorderResult
        grid = ATRBorderGrid()
        result = grid.calculate(pd.DataFrame())
        assert result.atr_value == 0

    def test_to_dict(self):
        from gold_edge.atr_border import ATRBorderGrid
        grid = ATRBorderGrid()
        df = _make_ohlcv(300)
        result = grid.calculate(df)
        d = result.to_dict()
        assert "ema_midline" in d
        assert "borders" in d
        assert "current_layer" in d

    def test_get_border_signal_long(self):
        from gold_edge.atr_border import ATRBorderGrid, ATRBorderResult
        grid = ATRBorderGrid()
        br = ATRBorderResult(current_layer=2, price_position_pct=0.2, is_near_border=True, nearest_border_name="outer_lower")
        signal = grid.get_border_signal(br, "LONG")
        assert signal["action"] == "ENTRY"

    def test_get_border_signal_short(self):
        from gold_edge.atr_border import ATRBorderGrid, ATRBorderResult
        grid = ATRBorderGrid()
        br = ATRBorderResult(current_layer=2, price_position_pct=0.8, is_near_border=True, nearest_border_name="outer_upper")
        signal = grid.get_border_signal(br, "SHORT")
        assert signal["action"] == "ENTRY"


# ===================================================================
# ATRRatioFilter Tests
# ===================================================================

class TestATRRatioFilter:
    """Tests for atr_filter.py"""

    def test_calculate_returns_filter_result(self):
        from gold_edge.atr_filter import ATRRatioFilter, ATRFilterResult
        filt = ATRRatioFilter()
        df = _make_ohlcv(300)
        result = filt.calculate(df)
        assert isinstance(result, ATRFilterResult)
        assert result.current_atr > 0
        assert result.atr_sma > 0

    def test_ratio_is_positive(self):
        from gold_edge.atr_filter import ATRRatioFilter
        filt = ATRRatioFilter()
        df = _make_ohlcv(300)
        result = filt.calculate(df)
        assert result.ratio > 0

    def test_zone_classifications(self):
        from gold_edge.atr_filter import ATRRatioFilter
        filt = ATRRatioFilter()
        df = _make_ohlcv(300)
        result = filt.calculate(df)
        assert result.zone in ("quiet", "ideal", "volatile", "extreme", "unknown")

    def test_insufficient_data(self):
        from gold_edge.atr_filter import ATRRatioFilter, ATRFilterResult
        filt = ATRRatioFilter()
        result = filt.calculate(pd.DataFrame())
        assert result.passes_filter is False

    def test_to_dict(self):
        from gold_edge.atr_filter import ATRRatioFilter
        filt = ATRRatioFilter()
        df = _make_ohlcv(300)
        result = filt.calculate(df)
        d = result.to_dict()
        assert "ratio" in d
        assert "passes_filter" in d
        assert "zone" in d

    def test_entry_adjustment_ideal(self):
        from gold_edge.atr_filter import ATRRatioFilter, ATRFilterResult
        filt = ATRRatioFilter()
        result = ATRFilterResult(ratio=0.5, passes_filter=True, zone="ideal")
        adj = filt.get_entry_adjustment(result)
        assert adj["allow_entry"] is True
        assert adj["risk_multiplier"] == 1.0

    def test_entry_adjustment_extreme(self):
        from gold_edge.atr_filter import ATRRatioFilter, ATRFilterResult
        filt = ATRRatioFilter()
        result = ATRFilterResult(ratio=3.0, passes_filter=False, zone="extreme")
        adj = filt.get_entry_adjustment(result)
        assert adj["allow_entry"] is False


# ===================================================================
# GoldEdgeMatrix Tests
# ===================================================================

class TestGoldEdgeMatrix:
    """Tests for entry_logic.py"""

    def test_evaluate_returns_matrix_result(self):
        from gold_edge.entry_logic import GoldEdgeMatrix, GoldEdgeMatrixResult
        matrix = GoldEdgeMatrix(min_gec_score=0.1, min_combined_score=0.1)
        df = _make_ohlcv(300)
        result = matrix.evaluate(df)
        assert isinstance(result, GoldEdgeMatrixResult)
        assert result.action in ("ENTRY", "WATCH", "NO_TRADE")

    def test_to_dict(self):
        from gold_edge.entry_logic import GoldEdgeMatrix
        matrix = GoldEdgeMatrix(min_gec_score=0.1, min_combined_score=0.1)
        df = _make_ohlcv(300)
        result = matrix.evaluate(df)
        d = result.to_dict()
        assert "action" in d
        assert "combined_score" in d
        assert "gec_score" in d
        assert "border_score" in d
        assert "filter_score" in d

    def test_entry_has_price_levels(self):
        from gold_edge.entry_logic import GoldEdgeMatrix
        # Use very low thresholds to force an entry
        matrix = GoldEdgeMatrix(min_gec_score=0.01, min_combined_score=0.01)
        df = _make_ohlcv(300)
        result = matrix.evaluate(df)
        if result.action == "ENTRY":
            assert result.entry_price > 0
            assert result.stop_loss > 0
            assert result.take_profit > 0
            assert result.risk_reward_ratio > 0

    def test_no_trade_when_neutral(self):
        from gold_edge.entry_logic import GoldEdgeMatrix
        # With default thresholds, most synthetic data produces NEUTRAL or low scores
        matrix = GoldEdgeMatrix(min_gec_score=0.9, min_combined_score=0.9)
        df = _make_ohlcv(300)
        result = matrix.evaluate(df)
        assert result.action == "NO_TRADE"


# ===================================================================
# GoldEdgeService Tests
# ===================================================================

class TestGoldEdgeService:
    """Tests for services.py"""

    def test_init_defaults(self):
        from gold_edge.services import GoldEdgeService
        svc = GoldEdgeService()
        assert svc.gec is not None
        assert svc.atr_border is not None
        assert svc.atr_filter is not None
        assert svc.matrix is not None

    @patch("gold_edge.services.GoldEdgeService._fetch_ohlcv")
    @patch("gold_edge.services.GoldEdgeService._fetch_dxy", return_value=None)
    def test_run_pipeline_with_data(self, mock_dxy, mock_fetch):
        from gold_edge.services import GoldEdgeService
        mock_fetch.return_value = _make_ohlcv(300)
        svc = GoldEdgeService()
        result = svc.run_pipeline("XAUUSD", "H1")
        assert result.action in ("ENTRY", "WATCH", "NO_TRADE")

    @patch("gold_edge.services.GoldEdgeService._fetch_ohlcv", return_value=pd.DataFrame())
    def test_run_pipeline_insufficient_data(self, mock_fetch):
        from gold_edge.services import GoldEdgeService
        svc = GoldEdgeService()
        result = svc.run_pipeline("XAUUSD", "H1")
        assert result.action == "NO_TRADE"
        assert "insufficient_data" in result.rejection_reasons

    def test_build_matrix_from_config(self):
        from gold_edge.services import GoldEdgeService
        from gold_edge.entry_logic import GoldEdgeMatrix
        svc = GoldEdgeService()
        config = {
            "momentum_weight": 0.25,
            "trend_weight": 0.25,
            "volatility_weight": 0.25,
            "dxy_correlation_weight": 0.25,
            "min_gec_score": 0.3,
            "min_combined_score": 0.4,
        }
        matrix = svc._build_matrix_from_config(config)
        assert isinstance(matrix, GoldEdgeMatrix)
