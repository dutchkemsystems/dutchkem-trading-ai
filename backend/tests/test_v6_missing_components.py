"""
Tests for V6 missing components:
  - MarketScanner
  - AIEngine
  - HMMRegimeDetector
  - FIPSEncryption
  - SecurityLayer (facade)
"""

import os
import sys

import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ====================================================================
# MarketScanner
# ====================================================================

class TestMarketScanner:
    """Tests for ml.market_scanner.MarketScanner."""

    def test_default_symbols_count_gte_28(self):
        from ml.market_scanner import MarketScanner
        assert len(MarketScanner.DEFAULT_SYMBOLS) >= 28

    def test_scan_all_instruments_filters_by_spread(self):
        from ml.market_scanner import MarketScanner
        scanner = MarketScanner(max_spread=0.5, min_volume=100)
        market_data = {
            "EURUSD": {"spread": 0.3, "volume": 500, "volatility": 1.0},
            "USDTRY": {"spread": 2.0, "volume": 500, "volatility": 1.0},
        }
        result = scanner.scan_all_instruments(market_data)
        symbols = [r["symbol"] for r in result]
        assert "EURUSD" in symbols
        assert "USDTRY" not in symbols

    def test_score_opportunity_range(self):
        from ml.market_scanner import MarketScanner
        scanner = MarketScanner()
        score = scanner.score_opportunity({
            "spread": 0.2, "volume": 1000, "volatility": 1.0,
        })
        assert 0.0 <= score <= 100.0

    def test_get_opportunities_after_scan(self):
        from ml.market_scanner import MarketScanner
        scanner = MarketScanner(max_spread=0.5, min_volume=100)
        market_data = {
            "EURUSD": {"spread": 0.3, "volume": 500, "volatility": 1.0},
            "GBPUSD": {"spread": 0.4, "volume": 300, "volatility": 0.8},
        }
        scanner.scan_all_instruments(market_data)
        opps = scanner.get_opportunities(top_n=5)
        assert len(opps) <= 5

    def test_filter_by_spread(self):
        from ml.market_scanner import MarketScanner
        scanner = MarketScanner()
        items = [
            {"spread": 0.1, "volume": 100},
            {"spread": 0.8, "volume": 200},
        ]
        filtered = scanner.filter_by_spread(items, max_spread=0.5)
        assert len(filtered) == 1
        assert filtered[0]["spread"] == 0.1

    def test_filter_by_volume(self):
        from ml.market_scanner import MarketScanner
        scanner = MarketScanner()
        items = [
            {"spread": 0.1, "volume": 50},
            {"spread": 0.1, "volume": 200},
        ]
        filtered = scanner.filter_by_volume(items, min_volume=100)
        assert len(filtered) == 1
        assert filtered[0]["volume"] == 200


# ====================================================================
# AIEngine
# ====================================================================

class TestAIEngine:
    """Tests for ml.ai_engine.AIEngine."""

    def test_initialization(self):
        from ml.ai_engine import AIEngine
        engine = AIEngine()
        engine.initialize()
        assert engine._initialized is True

    def test_component_health_dict(self):
        from ml.ai_engine import AIEngine
        engine = AIEngine()
        engine.initialize()
        health = engine.get_health()
        assert isinstance(health, dict)

    def test_predict_returns_dict(self):
        from ml.ai_engine import AIEngine
        engine = AIEngine()
        engine.initialize()
        result = engine.predict("EURUSD", {})
        assert isinstance(result, dict)
        assert "regime" in result
        assert "direction" in result
        assert "confidence" in result

    def test_get_regime_returns_dict(self):
        from ml.ai_engine import AIEngine
        engine = AIEngine()
        engine.initialize()
        result = engine.get_regime({})
        assert isinstance(result, dict)
        assert "regime" in result


# ====================================================================
# HMMRegimeDetector
# ====================================================================

class TestHMMRegimeDetector:
    """Tests for ml.models.hmm_regime_detector.HMMRegimeDetector."""

    def test_initialization(self):
        from ml.models.hmm_regime_detector import HMMRegimeDetector
        detector = HMMRegimeDetector()
        assert detector.n_regimes == 5
        assert detector._fitted is False

    def test_predict_before_fit_returns_regime_string(self):
        from ml.models.hmm_regime_detector import HMMRegimeDetector
        detector = HMMRegimeDetector()
        sample = [0.01, -0.005, 0.02, -0.01, 0.003,
                  0.008, -0.002, 0.015, -0.007, 0.004,
                  0.01, -0.005, 0.02, -0.01, 0.003,
                  0.008, -0.002, 0.015, -0.007, 0.004]
        result = detector.predict(sample)
        assert isinstance(result, str)
        assert result in HMMRegimeDetector.REGIMES or result == "UNKNOWN"

    def test_predict_proba_before_fit(self):
        from ml.models.hmm_regime_detector import HMMRegimeDetector
        detector = HMMRegimeDetector()
        sample = [0.01, -0.005, 0.02, -0.01, 0.003,
                  0.008, -0.002, 0.015, -0.007, 0.004,
                  0.01, -0.005, 0.02, -0.01, 0.003,
                  0.008, -0.002, 0.015, -0.007, 0.004]
        result = detector.predict_proba(sample)
        assert isinstance(result, dict)

    def test_fit_insufficient_data(self):
        from ml.models.hmm_regime_detector import HMMRegimeDetector
        detector = HMMRegimeDetector()
        result = detector.fit([0.01, 0.02])
        assert isinstance(result, dict)


# ====================================================================
# FIPSEncryption
# ====================================================================

class TestFIPSEncryption:
    """Tests for security.fips_encryption.FIPSEncryption."""

    def test_generate_key_32_bytes(self):
        from security.fips_encryption import FIPSEncryption
        key = FIPSEncryption.generate_key()
        assert len(key) == 32

    def test_encrypt_decrypt_roundtrip(self):
        from security.fips_encryption import FIPSEncryption
        fips = FIPSEncryption()
        key = FIPSEncryption.generate_key()
        plaintext = "Hello, FIPS world!"
        encrypted = fips.encrypt(plaintext, key)
        decrypted = fips.decrypt(
            encrypted["ciphertext"], key,
            encrypted["nonce"], encrypted["tag"],
        )
        assert decrypted == plaintext

    def test_encrypt_field_decrypt_field(self):
        from security.fips_encryption import FIPSEncryption
        fips = FIPSEncryption()
        original = "sensitive_data_123"
        encrypted = fips.encrypt_field(original, "test_field")
        decrypted = fips.decrypt_field(encrypted, "test_field")
        assert decrypted == original

    def test_hash_password_format(self):
        from security.fips_encryption import FIPSEncryption
        hashed = FIPSEncryption.hash_password("my_password")
        assert "$" in hashed
        parts = hashed.split("$")
        assert len(parts) == 2

    def test_verify_password_correct(self):
        from security.fips_encryption import FIPSEncryption
        hashed = FIPSEncryption.hash_password("test_pass")
        assert FIPSEncryption.verify_password("test_pass", hashed) is True

    def test_verify_password_incorrect(self):
        from security.fips_encryption import FIPSEncryption
        hashed = FIPSEncryption.hash_password("test_pass")
        assert FIPSEncryption.verify_password("wrong_pass", hashed) is False

    def test_verify_password_malformed(self):
        from security.fips_encryption import FIPSEncryption
        assert FIPSEncryption.verify_password("pw", "no_dollar_sign") is False


# ====================================================================
# SecurityLayer (facade)
# ====================================================================

class TestSecurityFacade:
    """Tests for security.facade.SecurityLayer."""

    def test_initialization(self):
        from security.facade import SecurityLayer
        layer = SecurityLayer()
        layer.initialize()
        assert layer._initialized is True

    def test_security_status_dict(self):
        from security.facade import SecurityLayer
        layer = SecurityLayer()
        layer.initialize()
        status = layer.get_security_status()
        assert isinstance(status, dict)
        assert "component_health" in status
        assert status["total_components"] == 7

    def test_encrypt_sensitive_data(self):
        from security.facade import SecurityLayer
        layer = SecurityLayer()
        layer.initialize()
        data = {"name": "John", "secret": "abc123"}
        encrypted = layer.encrypt_sensitive_data(data, ["secret"])
        assert "name" in encrypted
        assert "secret" in encrypted

    def test_log_security_event_no_error(self):
        from security.facade import SecurityLayer
        layer = SecurityLayer()
        layer.initialize()
        # Should not raise
        layer.log_security_event("test_event", {"detail": "test"})
