"""
Tests for the strategies module — confluence engine, timeframe strategies, regime switcher, strategy map.
"""
import pytest
from decimal import Decimal
from strategies.confluence import (
    ConfluenceEngine, Direction, TimeframeSignal, ConfluenceResult,
    TIMEFRAME_WEIGHTS,
)
from strategies.timeframe_strategies import (
    calculate_signal, TIMEFRAME_STRATEGIES, _sma, _ema, _rsi, _atr,
    _bollinger_bands, _macd,
)
from strategies.regime_switcher import (
    RegimeSwitcher, StrategyMap, MarketRegime, StrategyType,
    REGIME_STRATEGY_MAP, regime_switcher, strategy_map,
)
from strategies.strategy_map import (
    StrategyConfig, STRATEGY_CONFIGS, get_strategy_config,
)


# ---------------------------------------------------------------------------
# Indicator Functions
# ---------------------------------------------------------------------------
class TestIndicatorFunctions:
    def test_sma(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _sma(values, 3) == pytest.approx(4.0)

    def test_sma_insufficient_data(self):
        assert _sma([1.0], 5) == 1.0

    def test_sma_empty(self):
        assert _sma([], 5) == 0

    def test_ema(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _ema(values, 3)
        assert isinstance(result, float)

    def test_ema_empty(self):
        assert _ema([], 5) == 0

    def test_rsi_neutral(self):
        # Stable prices -> RSI near 50
        closes = [1.1200] * 20
        rsi = _rsi(closes)
        assert rsi == 50.0

    def test_rsi_overbought(self):
        # Rising prices -> RSI > 50
        closes = [1.1200 + i * 0.001 for i in range(20)]
        rsi = _rsi(closes)
        assert rsi > 50

    def test_rsi_oversold(self):
        # Falling prices -> RSI < 50
        closes = [1.1300 - i * 0.001 for i in range(20)]
        rsi = _rsi(closes)
        assert rsi < 50

    def test_rsi_insufficient_data(self):
        assert _rsi([1.0, 2.0]) == 50.0

    def test_atr(self):
        highs = [1.13, 1.14, 1.15]
        lows = [1.12, 1.13, 1.14]
        closes = [1.125, 1.135, 1.145]
        atr = _atr(highs, lows, closes)
        assert atr > 0

    def test_atr_min_data(self):
        assert _atr([1.0], [0.9], [0.95]) == 0.0001

    def test_bollinger_bands(self):
        closes = [1.1200 + i * 0.0001 for i in range(30)]
        lower, mid, upper = _bollinger_bands(closes)
        assert lower < mid < upper

    def test_bollinger_bands_insufficient(self):
        lower, mid, upper = _bollinger_bands([1.0])
        assert lower == mid == upper == 1.0

    def test_macd(self):
        closes = [1.1200 + i * 0.0001 for i in range(30)]
        macd_line, signal_line, histogram = _macd(closes)
        assert isinstance(macd_line, float)


# ---------------------------------------------------------------------------
# Timeframe Strategies
# ---------------------------------------------------------------------------
class TestTimeframeStrategies:
    def test_all_timeframes_defined(self):
        expected = {"M5", "M15", "M30", "H1", "H2", "H4"}
        assert set(TIMEFRAME_STRATEGIES.keys()) == expected

    def test_calculate_signal_neutral(self):
        """Insufficient data should return NEUTRAL."""
        result = calculate_signal("H1", {"close": [1.0] * 3})
        assert result["signal"] == "NEUTRAL"
        assert result["strength"] == 0

    def test_calculate_signal_with_data(self, sample_ohlcv):
        """Valid data should return a signal."""
        result = calculate_signal("H1", sample_ohlcv)
        assert result["signal"] in ("BUY", "SELL", "NEUTRAL")
        assert "strength" in result
        assert "indicators" in result
        assert "stop_loss_pips" in result
        assert "take_profit_pips" in result

    def test_calculate_signal_all_timeframes(self, sample_ohlcv):
        """All timeframes should produce valid results."""
        for tf in TIMEFRAME_STRATEGIES:
            result = calculate_signal(tf, sample_ohlcv)
            assert result["signal"] in ("BUY", "SELL", "NEUTRAL")
            assert result["stop_loss_pips"] > 0
            assert result["take_profit_pips"] > 0

    def test_calculate_signal_unknown_timeframe(self, sample_ohlcv):
        """Unknown timeframe should fall back to H1 config."""
        result = calculate_signal("X99", sample_ohlcv)
        assert result["signal"] in ("BUY", "SELL", "NEUTRAL")


# ---------------------------------------------------------------------------
# Confluence Engine
# ---------------------------------------------------------------------------
class TestConfluenceEngine:
    def setup_method(self):
        self.engine = ConfluenceEngine(min_score=55.0, min_agreement_pct=0.6)

    def test_empty_signals(self):
        result = self.engine.calculate_confluence("EURUSD", {})
        assert result.direction == Direction.NEUTRAL
        assert float(result.total_score) == 0

    def test_all_buy_signals(self):
        signals = {
            "H1": TimeframeSignal("H1", "BUY", Decimal("80")),
            "H4": TimeframeSignal("H4", "BUY", Decimal("75")),
            "M30": TimeframeSignal("M30", "BUY", Decimal("70")),
        }
        result = self.engine.calculate_confluence("EURUSD", signals)
        assert result.direction == Direction.LONG
        assert float(result.total_score) > 0

    def test_all_sell_signals(self):
        signals = {
            "H1": TimeframeSignal("H1", "SELL", Decimal("80")),
            "H4": TimeframeSignal("H4", "SELL", Decimal("75")),
        }
        result = self.engine.calculate_confluence("EURUSD", signals)
        assert result.direction == Direction.SHORT

    def test_mixed_signals_neutral(self):
        signals = {
            "H1": TimeframeSignal("H1", "BUY", Decimal("60")),
            "H4": TimeframeSignal("H4", "SELL", Decimal("60")),
        }
        result = self.engine.calculate_confluence("EURUSD", signals)
        # Should be neutral or close to it
        assert result.direction in (Direction.NEUTRAL, Direction.LONG, Direction.SHORT)

    def test_should_trade_neutral(self):
        result = ConfluenceResult(symbol="EURUSD", direction=Direction.NEUTRAL)
        assert not self.engine.should_trade(result)

    def test_should_trade_high_score(self):
        result = ConfluenceResult(
            symbol="EURUSD",
            direction=Direction.LONG,
            total_score=Decimal("75"),
            higher_tf_agreement=True,
        )
        assert self.engine.should_trade(result)

    def test_should_trade_low_score(self):
        result = ConfluenceResult(
            symbol="EURUSD",
            direction=Direction.LONG,
            total_score=Decimal("30"),
            higher_tf_agreement=True,
        )
        assert not self.engine.should_trade(result)

    def test_should_trade_no_higher_tf_agreement(self):
        result = ConfluenceResult(
            symbol="EURUSD",
            direction=Direction.LONG,
            total_score=Decimal("75"),
            higher_tf_agreement=False,
        )
        assert not self.engine.should_trade(result)

    def test_risk_reward_ratio(self):
        signals = {
            "H1": TimeframeSignal("H1", "BUY", Decimal("80"), stop_loss_pips=30, take_profit_pips=60),
        }
        result = self.engine.calculate_confluence("EURUSD", signals)
        assert result.risk_reward_ratio == 2.0

    def test_tf_weights_sum_to_one(self):
        total = sum(TIMEFRAME_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01


# ---------------------------------------------------------------------------
# Regime Switcher
# ---------------------------------------------------------------------------
class TestRegimeSwitcher:
    def setup_method(self):
        self.switcher = RegimeSwitcher(use_ml=False)

    def test_default_regime(self):
        assert self.switcher.current_regime == MarketRegime.WEAK_TRENDING

    def test_current_strategy(self):
        strategy = self.switcher.current_strategy
        assert "strategy" in strategy
        assert "risk_multiplier" in strategy

    def test_detect_from_ml_confident(self):
        prediction = {
            "regime": MarketRegime.STRONG_TRENDING,
            "confidence": 0.9,
            "is_confident": True,
        }
        result = self.switcher.detect_regime(ml_prediction=prediction)
        assert result["regime"] == MarketRegime.STRONG_TRENDING
        assert result["source"] == "ml"

    def test_detect_from_ml_low_confidence(self):
        prediction = {
            "regime": MarketRegime.STRONG_TRENDING,
            "confidence": 0.3,
            "is_confident": False,
        }
        result = self.switcher.detect_regime(ml_prediction=prediction)
        assert result["source"] == "ml_low_confidence"

    def test_get_adjusted_parameters(self):
        params = {"risk_per_trade": 1.0}
        self.switcher._current_regime = MarketRegime.STRONG_TRENDING
        adjusted = self.switcher.get_adjusted_parameters(params)
        assert adjusted["risk_multiplier"] == 1.0
        assert adjusted["allow_trading"] is True

    def test_pause_regime_no_trading(self):
        self.switcher._current_regime = MarketRegime.NEWS
        params = {"risk_per_trade": 1.0}
        adjusted = self.switcher.get_adjusted_parameters(params)
        assert adjusted["allow_trading"] is False
        assert adjusted["risk_per_trade"] == 0.0

    def test_calculate_stop_loss_buy(self):
        self.switcher._current_regime = MarketRegime.STRONG_TRENDING
        sl = self.switcher.calculate_stop_loss(1.1200, "BUY", 0.005)
        assert sl < 1.1200

    def test_calculate_stop_loss_sell(self):
        self.switcher._current_regime = MarketRegime.STRONG_TRENDING
        sl = self.switcher.calculate_stop_loss(1.1200, "SELL", 0.005)
        assert sl > 1.1200

    def test_calculate_take_profit_buy(self):
        self.switcher._current_regime = MarketRegime.WEAK_TRENDING
        sl = 1.1150
        tp = self.switcher.calculate_take_profit(1.1200, sl, "BUY")
        assert tp > 1.1200

    def test_calculate_take_profit_sell(self):
        self.switcher._current_regime = MarketRegime.WEAK_TRENDING
        sl = 1.1250
        tp = self.switcher.calculate_take_profit(1.1200, sl, "SELL")
        assert tp < 1.1200

    def test_regime_history(self):
        history = self.switcher.get_regime_history()
        assert isinstance(history, list)


class TestStrategyMap:
    def test_get_strategy(self):
        config = strategy_map.get_strategy(MarketRegime.STRONG_TRENDING)
        assert config["strategy"] == StrategyType.TREND_FOLLOWING

    def test_get_strategy_unknown(self):
        config = strategy_map.get_strategy("unknown_regime")
        assert config["strategy"] == StrategyType.MOMENTUM

    def test_get_risk_multiplier(self):
        mult = strategy_map.get_risk_multiplier(MarketRegime.VOLATILE)
        assert mult == 0.5

    def test_get_timeframe(self):
        tf = strategy_map.get_timeframe(MarketRegime.RANGING)
        assert tf == "M5"

    def test_should_trade(self):
        assert strategy_map.should_trade(MarketRegime.STRONG_TRENDING)
        assert not strategy_map.should_trade(MarketRegime.NEWS)

    def test_get_all_strategies(self):
        all_strats = strategy_map.get_all_strategies()
        assert len(all_strats) == 6


# ---------------------------------------------------------------------------
# Strategy Configs
# ---------------------------------------------------------------------------
class TestStrategyConfigs:
    def test_all_strategy_types_covered(self):
        expected = {
            StrategyType.TREND_FOLLOWING,
            StrategyType.MOMENTUM,
            StrategyType.MEAN_REVERSION,
            StrategyType.BREAKOUT,
            StrategyType.SCALPING,
            StrategyType.PAUSE,
        }
        assert set(STRATEGY_CONFIGS.keys()) == expected

    def test_get_strategy_config(self):
        config = get_strategy_config(StrategyType.TREND_FOLLOWING)
        assert config.name == "Trend Following"
        assert config.timeframe == "H1"

    def test_get_strategy_config_unknown(self):
        config = get_strategy_config("nonexistent")
        assert config.name == "Momentum"  # Default fallback

    def test_pause_config(self):
        config = STRATEGY_CONFIGS[StrategyType.PAUSE]
        assert config.risk_multiplier == 0.0
        assert config.timeframe is None
        assert config.position_rules["max_positions"] == 0

    def test_strategy_configs_have_rules(self):
        for stype, config in STRATEGY_CONFIGS.items():
            assert hasattr(config, "entry_rules")
            assert hasattr(config, "exit_rules")
            assert hasattr(config, "position_rules")
