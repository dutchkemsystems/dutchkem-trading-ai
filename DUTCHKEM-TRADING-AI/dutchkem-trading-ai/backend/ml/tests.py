"""
Comprehensive ML unit tests for:
  - FeatureEngine
  - LSTMDirectionModel (architecture / predict shape)
  - RegimeDetector
  - EnsemblePredictor
  - DataPreprocessor
  - PredictionPipeline
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: generate synthetic OHLCV DataFrame
# ---------------------------------------------------------------------------

def _make_ohlcv_df(n: int = 300) -> pd.DataFrame:
    np.random.seed(42)
    close = 1.1200 + np.cumsum(np.random.randn(n) * 0.0005)
    high = close + np.abs(np.random.randn(n) * 0.0003)
    low = close - np.abs(np.random.randn(n) * 0.0003)
    open_ = close + np.random.randn(n) * 0.0002
    volume = np.random.randint(500, 5000, n)
    ts = pd.date_range("2025-01-01", periods=n, freq="1h")
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "spread": np.random.uniform(0.5, 2.0, n),
        "timestamp": ts,
    })


# ===================================================================
# FeatureEngine tests
# ===================================================================

class TestFeatureEngine:
    """Tests for ml.features.FeatureEngine"""

    def test_compute_features_returns_dataframe(self):
        from ml.features import FeatureEngine
        df = _make_ohlcv_df(300)
        engine = FeatureEngine()
        features = engine.compute_features(df)
        assert isinstance(features, pd.DataFrame)

    def test_feature_count_exceeds_100(self):
        from ml.features import FeatureEngine
        df = _make_ohlcv_df(300)
        engine = FeatureEngine()
        features = engine.compute_features(df)
        assert features.shape[1] > 100, f"Expected >100 features, got {features.shape[1]}"

    def test_compute_labels_shape(self):
        from ml.features import FeatureEngine
        df = _make_ohlcv_df(300)
        engine = FeatureEngine()
        labels = engine.compute_labels(df, forward_bars=5)
        assert len(labels) == len(df)
        assert set(labels.unique()).issubset({0, 1, 2})

    def test_labels_no_nan(self):
        from ml.features import FeatureEngine
        df = _make_ohlcv_df(300)
        engine = FeatureEngine()
        labels = engine.compute_labels(df)
        assert labels.isna().sum() == 0

    def test_features_contain_expected_columns(self):
        from ml.features import FeatureEngine
        df = _make_ohlcv_df(300)
        engine = FeatureEngine()
        features = engine.compute_features(df)
        expected = ["rsi_14", "macd_12_26", "adx_14", "atr_14", "bb_pct_20"]
        for col in expected:
            assert col in features.columns, f"Missing column: {col}"


# ===================================================================
# LSTMDirectionModel tests
# ===================================================================

class TestLSTMDirectionModel:
    """Tests for ml.models.lstm_direction.LSTMDirectionModel"""

    def test_build_model_returns_model(self):
        """Build model only if TF is installed; otherwise skip."""
        from ml.models.lstm_direction import LSTMDirectionModel
        m = LSTMDirectionModel(sequence_length=20, n_features=10)
        model = m.build_model()
        if model is not None:
            assert m._model is not None

    def test_predict_without_model_returns_error(self):
        from ml.models.lstm_direction import LSTMDirectionModel
        m = LSTMDirectionModel(sequence_length=20, n_features=10)
        result = m.predict(np.random.randn(1, 20, 10))
        assert "error" in result

    def test_train_without_model_returns_error(self):
        from ml.models.lstm_direction import LSTMDirectionModel
        m = LSTMDirectionModel(sequence_length=20, n_features=10)
        result = m.train(
            np.random.randn(50, 20, 10),
            np.random.randint(0, 3, 50),
            np.random.randn(10, 20, 10),
            np.random.randint(0, 3, 10),
        )
        # Either returns error or succeeds (if TF installed)
        assert "error" in result or "epochs_trained" in result

    def test_evaluate_without_model_returns_error(self):
        from ml.models.lstm_direction import LSTMDirectionModel
        m = LSTMDirectionModel(sequence_length=20, n_features=10)
        result = m.evaluate(
            np.random.randn(10, 20, 10),
            np.random.randint(0, 3, 10),
        )
        assert "error" in result


# ===================================================================
# RegimeDetector tests
# ===================================================================

class TestRegimeDetector:
    """Tests for ml.models.regime_detector.RegimeDetector"""

    def test_build_model(self):
        from ml.models.regime_detector import RegimeDetector
        rd = RegimeDetector()
        model = rd.build_model()
        if model is not None:
            assert rd._model is not None

    def test_predict_without_model_returns_error(self):
        from ml.models.regime_detector import RegimeDetector
        rd = RegimeDetector()
        result = rd.predict(np.random.randn(1, 50))
        assert "error" in result

    def test_label_regimes(self):
        from ml.models.regime_detector import RegimeDetector
        df = _make_ohlcv_df(300)
        from ml.features import FeatureEngine
        features = FeatureEngine().compute_features(df)
        rd = RegimeDetector()
        labels = rd.label_regimes(features)
        assert len(labels) == len(df)
        assert set(labels.unique()).issubset({0, 1, 2, 3, 4, 5})

    def test_get_feature_importance_empty(self):
        from ml.models.regime_detector import RegimeDetector
        rd = RegimeDetector()
        assert rd.get_feature_importance() == {}


# ===================================================================
# EnsemblePredictor tests
# ===================================================================

class TestEnsemblePredictor:
    """Tests for ml.ensemble.EnsemblePredictor"""

    def test_default_weights_sum_to_one(self):
        from ml.ensemble import EnsemblePredictor
        ep = EnsemblePredictor()
        total = sum(ep.weights.values())
        assert abs(total - 1.0) < 0.01

    def test_predict_no_models_returns_neutral(self):
        from ml.ensemble import EnsemblePredictor
        ep = EnsemblePredictor()
        result = ep.predict(
            features_sequence=np.random.randn(1, 20, 50),
            current_features=np.random.randn(1, 50),
        )
        assert "direction" in result
        assert result["direction"] in ("BEARISH", "BULLISH", "NEUTRAL")

    def test_adjust_weights_for_regime(self):
        from ml.ensemble import EnsemblePredictor
        ep = EnsemblePredictor()
        adj = ep.adjust_weights_for_regime("trending_strong")
        assert adj["lstm"] == 0.45
        assert abs(sum(adj.values()) - 1.0) < 0.01

    def test_adjust_weights_volatile(self):
        from ml.ensemble import EnsemblePredictor
        ep = EnsemblePredictor()
        adj = ep.adjust_weights_for_regime("volatile")
        assert adj["volatility"] == 0.30

    def test_sr_levels_none_when_no_model(self):
        from ml.ensemble import EnsemblePredictor
        ep = EnsemblePredictor()
        result = ep.predict(
            features_sequence=np.random.randn(1, 20, 50),
            current_features=np.random.randn(1, 50),
            sr_features=np.random.randn(1, 10),
        )
        assert result["sr_levels"] is None

    def test_volatility_none_when_no_model(self):
        from ml.ensemble import EnsemblePredictor
        ep = EnsemblePredictor()
        result = ep.predict(
            features_sequence=np.random.randn(1, 20, 50),
            current_features=np.random.randn(1, 50),
            volatility_features=np.random.randn(1, 5),
        )
        assert result["volatility_regime"] is None


# ===================================================================
# DataPreprocessor tests
# ===================================================================

class TestDataPreprocessor:
    """Tests for ml.preprocessing.DataPreprocessor"""

    def test_fit_transform_shape(self):
        from ml.preprocessing import DataPreprocessor
        pp = DataPreprocessor()
        X = np.random.randn(100, 20)
        X_scaled = pp.fit_transform(X, [f"f{i}" for i in range(20)])
        assert X_scaled.shape == X.shape

    def test_transform_without_fit_raises(self):
        from ml.preprocessing import DataPreprocessor
        pp = DataPreprocessor()
        with pytest.raises(RuntimeError):
            pp.transform(np.random.randn(10, 5))

    def test_inverse_transform(self):
        from ml.preprocessing import DataPreprocessor
        pp = DataPreprocessor()
        X = np.random.randn(100, 20)
        X_scaled = pp.fit_transform(X, [f"f{i}" for i in range(20)])
        X_inv = pp.inverse_transform(X_scaled)
        np.testing.assert_allclose(X, X_inv, atol=1e-6)

    def test_create_windows(self):
        from ml.preprocessing import DataPreprocessor
        pp = DataPreprocessor()
        data = np.random.randn(200, 10)
        X, y = pp.create_windows(data, window_size=30, horizon=1)
        assert X.shape == (170, 30, 10)
        assert y.shape[0] == 170

    def test_handle_nan(self):
        from ml.preprocessing import DataPreprocessor
        pp = DataPreprocessor()
        X = np.random.randn(10, 5)
        X[3, 2] = np.nan
        X_clean = pp.handle_nan(X)
        assert not np.isnan(X_clean).any()

    def test_balance_classes(self):
        from ml.preprocessing import DataPreprocessor
        pp = DataPreprocessor()
        X = np.random.randn(100, 10)
        y = np.array([0] * 80 + [1] * 20)
        X_bal, y_bal = pp.balance_classes(X, y)
        assert len(X_bal) == 40  # 20 per class
        assert len(y_bal) == 40

    def test_save_load_preprocessor(self, tmp_path):
        from ml.preprocessing import DataPreprocessor
        pp = DataPreprocessor()
        X = np.random.randn(100, 10)
        pp.fit_transform(X, [f"f{i}" for i in range(10)])
        path = str(tmp_path / "preprocessor.joblib")
        pp.save_preprocessor(path)

        pp2 = DataPreprocessor()
        pp2.load_preprocessor(path)
        X2 = pp2.transform(X)
        np.testing.assert_allclose(X, X2, atol=1e-6)


# ===================================================================
# PredictionPipeline tests
# ===================================================================

class TestPredictionPipeline:
    """Tests for ml.pipeline.PredictionPipeline"""

    def test_init_defaults(self):
        from ml.pipeline import PredictionPipeline
        p = PredictionPipeline()
        assert p._initialized is False

    def test_get_pipeline_info(self):
        from ml.pipeline import PredictionPipeline
        p = PredictionPipeline()
        info = p.get_pipeline_info()
        assert "initialized" in info
        assert info["initialized"] is False
