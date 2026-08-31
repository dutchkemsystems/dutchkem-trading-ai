"""
V6.5 ULTIMATE ENHANCED ORCHESTRATOR
Integrates all 10 V6.5 enhancements with the existing V6 trading system.

Phases:
  1. Market Scan      — Scan 3-10 instruments for opportunities
  2. AI & Regime      — Ensemble prediction + regime detection
  3. Sentiment        — News + social + order flow sentiment (NEW)
  4. News Strategy    — Economic event awareness (NEW)
  5. Order Flow       — Institutional activity detection (NEW)
  6. Pattern Recog    — Deep learning candlestick patterns (NEW)
  7. Multi-TF         — Timeframe confluence (NEW)
  8. Signal Generation — Combined signal from all sources
  9. Risk Management  — Dynamic sizing + correlation + volatility
  10. Stop-Loss       — Adaptive stop calculation (NEW)
  11. Take-Profit     — Adaptive TP with partial closes (NEW)
  12. Diversification — Portfolio diversification check (NEW)
  13. Execution       — Spread/slippage checks, order routing
  14. Exit Management — Time-based progressive exits
  15. Learning        — Self-optimizing parameters (NEW)
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ml.cache import MLCache

# V6 additions — lazy imports to avoid circular deps
try:
    from ml.ai_engine import AIEngine
    _AI_ENGINE_AVAILABLE = True
except ImportError:
    AIEngine = None  # type: ignore[assignment,misc]
    _AI_ENGINE_AVAILABLE = False

try:
    from ml.market_scanner import MarketScanner
    _MARKET_SCANNER_AVAILABLE = True
except ImportError:
    MarketScanner = None  # type: ignore[assignment,misc]
    _MARKET_SCANNER_AVAILABLE = False

try:
    from security.facade import SecurityLayer
    _SECURITY_LAYER_AVAILABLE = True
except ImportError:
    SecurityLayer = None  # type: ignore[assignment,misc]
    _SECURITY_LAYER_AVAILABLE = False

try:
    from ml.models.hmm_regime_detector import HMMRegimeDetector
    _HMM_REGIME_AVAILABLE = True
except ImportError:
    HMMRegimeDetector = None  # type: ignore[assignment,misc]
    _HMM_REGIME_AVAILABLE = False

logger = logging.getLogger("ml.v65_orchestrator")


class _PhaseTimer:
    def __init__(self, phase_name: str, result_dict: dict):
        self.phase_name = phase_name
        self.result_dict = result_dict
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.result_dict[self.phase_name] = round((time.perf_counter() - self.start_time) * 1000, 2)
        return False


class V65TradingOrchestrator:
    """
    V6.5 Master Orchestrator — integrates all 10 enhancements with V6 core.
    """

    def __init__(self):
        # V6 core components (lazy loaded)
        self.ensemble = None
        self.regime_detector = None
        self.meta_learner = None
        self.asset_ensembles = None
        self.transfer_learning = None
        self.dynamic_allocation = None
        self.correlation_manager = None
        self.volatility_scaler = None
        self.dynamic_kelly = None
        self.strategy_diversification = None
        self.time_based_exit = None
        self.execution_optimizer = None

        # V6 additions (lazy loaded)
        self.ai_engine = None
        self.market_scanner = None
        self.security_layer = None
        self.hmm_regime = None

        # V6.5 enhancements (lazy loaded)
        self.sentiment_analyzer = None
        self.news_trader = None
        self.order_flow_analyzer = None
        self.pattern_recognizer = None
        self.multi_tf_analyzer = None
        self.dynamic_stop_loss = None
        self.risk_sizer = None
        self.diversification = None
        self.adaptive_tp = None
        self.optimizer = None

        # Persistent position tracking across cycles
        self.open_positions: List[Dict] = []

        # Component health tracking
        self._component_health: Dict[str, bool] = {}

        self._initialized = False
        self._cycle_count = 0
        self._total_cycle_time_ms = 0.0
        self._last_phase_timings: Dict[str, float] = {}
        self._closed_this_cycle = False

    def _lazy_load(self, module_path: str, attr_name: str, friendly_name: str):
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, attr_name)
            instance = cls()
            logger.info("V6.5 loaded: %s", friendly_name)
            self._component_health[friendly_name] = True
            return instance
        except (ImportError, ModuleNotFoundError) as e:
            # Expected when optional components are not installed
            logger.debug("V6.5 optional component not installed: %s (%s)", friendly_name, e)
            self._component_health[friendly_name] = False
            return None
        except AttributeError as e:
            # Class not found in module — likely a code-level issue
            logger.error("V6.5 component class missing: %s (%s)", friendly_name, e)
            self._component_health[friendly_name] = False
            return None
        except Exception as e:
            # Unexpected error during instantiation
            logger.error("V6.5 component failed to initialize: %s (%s)", friendly_name, e, exc_info=True)
            self._component_health[friendly_name] = False
            return None

    def initialize(self):
        if self._initialized:
            return

        # V6 core
        self.ensemble = self._lazy_load("ml.pipeline", "pipeline", "V3 Pipeline")
        self.regime_detector = self._lazy_load("ml.models.regime_detector", "RegimeDetector", "RegimeDetector")
        self.meta_learner = self._lazy_load("ml.meta_learner", "MetaLearner", "MetaLearner")
        self.asset_ensembles = self._lazy_load("ml.asset_ensemble", "AssetClassEnsemble", "AssetEnsemble")
        self.transfer_learning = self._lazy_load("ml.transfer_learning", "TransferLearning", "TransferLearning")
        self.dynamic_allocation = self._lazy_load("ml.dynamic_allocation", "DynamicAssetAllocation", "DynAllocation")
        self.correlation_manager = self._lazy_load("ml.dynamic_allocation", "CorrelationManager", "CorrManager")
        self.volatility_scaler = self._lazy_load("ml.dynamic_allocation", "VolatilityScaler", "VolScaler")
        self.dynamic_kelly = self._lazy_load("ml.time_based_exit", "DynamicKelly", "DynKelly")
        self.strategy_diversification = self._lazy_load("ml.strategy_diversification", "StrategyDiversification", "StratDiv")
        self.time_based_exit = self._lazy_load("ml.time_based_exit", "TimeBasedExit", "TimeExit")
        self.execution_optimizer = self._lazy_load("ml.time_based_exit", "ExecutionOptimizer", "ExecOpt")

        # V6.5 enhancements
        self.sentiment_analyzer = self._lazy_load("ml.enhancements.sentiment_analyzer", "SentimentAnalyzer", "SentimentAnalyzer")
        self.news_trader = self._lazy_load("ml.enhancements.smart_news_trading", "SmartNewsTrading", "NewsTrader")
        self.order_flow_analyzer = self._lazy_load("ml.enhancements.order_flow_analyzer", "OrderFlowAnalyzer", "OrderFlow")
        self.pattern_recognizer = self._lazy_load("ml.enhancements.deep_pattern_recognizer", "DeepPatternRecognizer", "PatternRecog")
        self.multi_tf_analyzer = self._lazy_load("ml.enhancements.multi_timeframe_analyzer", "MultiTimeframeAnalyzer", "MultiTF")
        self.dynamic_stop_loss = self._lazy_load("ml.enhancements.dynamic_stop_loss", "DynamicStopLoss", "DynSL")
        self.risk_sizer = self._lazy_load("ml.enhancements.risk_adjusted_sizer", "RiskAdjustedSizer", "RiskSizer")
        self.diversification = self._lazy_load("ml.enhancements.artificial_diversification", "ArtificialDiversification", "Diversification")
        self.adaptive_tp = self._lazy_load("ml.enhancements.adaptive_take_profit", "AdaptiveTakeProfit", "AdaptiveTP")
        self.optimizer = self._lazy_load("ml.enhancements.self_optimizing_system", "SelfOptimizingSystem", "SelfOptimizer")

        # V6 additions — lazy-load new subsystems
        if _AI_ENGINE_AVAILABLE and AIEngine is not None:
            try:
                self.ai_engine = AIEngine()
                self.ai_engine.initialize()
                self._component_health["AIEngine"] = True
                logger.info("V6.5 loaded: AIEngine")
            except Exception as e:
                logger.error("V6.5 AIEngine init failed: %s", e)
                self._component_health["AIEngine"] = False

        if _MARKET_SCANNER_AVAILABLE and MarketScanner is not None:
            try:
                self.market_scanner = MarketScanner()
                self._component_health["MarketScanner"] = True
                logger.info("V6.5 loaded: MarketScanner")
            except Exception as e:
                logger.error("V6.5 MarketScanner init failed: %s", e)
                self._component_health["MarketScanner"] = False

        if _SECURITY_LAYER_AVAILABLE and SecurityLayer is not None:
            try:
                self.security_layer = SecurityLayer()
                self.security_layer.initialize()
                self._component_health["SecurityLayer"] = True
                logger.info("V6.5 loaded: SecurityLayer")
            except Exception as e:
                logger.error("V6.5 SecurityLayer init failed: %s", e)
                self._component_health["SecurityLayer"] = False

        if _HMM_REGIME_AVAILABLE and HMMRegimeDetector is not None:
            try:
                self.hmm_regime = HMMRegimeDetector()
                self._component_health["HMMRegimeDetector"] = True
                logger.info("V6.5 loaded: HMMRegimeDetector")
            except Exception as e:
                logger.error("V6.5 HMMRegimeDetector init failed: %s", e)
                self._component_health["HMMRegimeDetector"] = False

        self._initialized = True
        logger.info("V6.5 Orchestrator initialized — %d components loaded", self.component_count)

    @property
    def component_count(self) -> int:
        all_components = [
            self.ensemble, self.regime_detector, self.meta_learner, self.asset_ensembles,
            self.transfer_learning, self.dynamic_allocation, self.correlation_manager,
            self.volatility_scaler, self.dynamic_kelly, self.strategy_diversification,
            self.time_based_exit, self.execution_optimizer,
            self.sentiment_analyzer, self.news_trader, self.order_flow_analyzer,
            self.pattern_recognizer, self.multi_tf_analyzer, self.dynamic_stop_loss,
            self.risk_sizer, self.diversification, self.adaptive_tp, self.optimizer,
            self.ai_engine, self.market_scanner, self.security_layer, self.hmm_regime,
        ]
        return sum(1 for c in all_components if c is not None)

    # ── Market data cache for exit management ────────────────────────────
    _market_data_cache: Dict[str, Any] = {}

    def run_trading_cycle(self, market_data: Dict[str, Any], broker_client=None, trading_mode: str = "semi") -> Dict[str, Any]:
        self.initialize()
        cycle_start = time.perf_counter()
        result: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(), "version": "6.5",
            "phases": {}, "trade_executed": False, "timings": {},
        }

        # ── PHASE 0: Exit Management — runs FIRST every cycle ──────────
        # Check all open positions for TP/SL/time exits regardless of
        # whether a new signal is generated this cycle.
        with _PhaseTimer("phase0_exit_check_ms", result["timings"]):
            self._phase14_exit_management({}, market_data)

        # ── FIX 6: Trigger learning on any positions closed this cycle ──
        if self._closed_this_cycle:
            logger.info("Positions closed during exit management — triggering learning")
            self._phase15_learning({}, {})
            self._closed_this_cycle = False

        # ── PHASE 1: Market Scanning ──
        with _PhaseTimer("phase1_scan_ms", result["timings"]):
            scan_result = self._phase1_market_scan(market_data)
            result["phases"]["scan"] = scan_result

        if not scan_result.get("opportunities"):
            result["status"] = "NO_OPPORTUNITIES"
            self._record_cycle(cycle_start, result)
            return result

        # ── PHASE 2: AI & Regime Detection ──
        with _PhaseTimer("phase2_ai_ms", result["timings"]):
            ai_result = self._phase2_ai_analysis(market_data, scan_result)
            result["phases"]["ai"] = ai_result

        # ── PHASE 3: Sentiment Analysis (V6.5) ──
        with _PhaseTimer("phase3_sentiment_ms", result["timings"]):
            sentiment_result = self._phase3_sentiment(scan_result)
            result["phases"]["sentiment"] = sentiment_result

        # ── PHASE 4: News Strategy (V6.5) ──
        with _PhaseTimer("phase4_news_ms", result["timings"]):
            news_result = self._phase4_news_strategy(scan_result)
            result["phases"]["news"] = news_result

        # ── PHASE 5: Order Flow (V6.5) ──
        with _PhaseTimer("phase5_orderflow_ms", result["timings"]):
            orderflow_result = self._phase5_order_flow(scan_result, market_data)
            result["phases"]["orderflow"] = orderflow_result

        # ── PHASE 6: Pattern Recognition (V6.5) ──
        with _PhaseTimer("phase6_pattern_ms", result["timings"]):
            pattern_result = self._phase6_pattern_recognition(scan_result)
            result["phases"]["pattern"] = pattern_result

        # ── PHASE 7: Multi-Timeframe (V6.5) ──
        with _PhaseTimer("phase7_multitf_ms", result["timings"]):
            tf_result = self._phase7_multi_tf(scan_result, market_data)
            result["phases"]["multitf"] = tf_result

        # ── PHASE 8: Signal Generation (Combined) ──
        with _PhaseTimer("phase8_signal_ms", result["timings"]):
            signal_result = self._phase8_signal_generation(
                scan_result, ai_result, sentiment_result, news_result,
                orderflow_result, pattern_result, tf_result,
            )
            result["phases"]["signal"] = signal_result

        if not signal_result.get("signal"):
            result["status"] = "NO_SIGNAL"
            self._record_cycle(cycle_start, result)
            return result

        # ── PHASE 9: Risk Management ──
        with _PhaseTimer("phase9_risk_ms", result["timings"]):
            risk_result = self._phase9_risk_management(signal_result, market_data)
            result["phases"]["risk"] = risk_result

        if not risk_result.get("approved"):
            result["status"] = "RISK_REJECTED"
            self._record_cycle(cycle_start, result)
            return result

        # ── PHASE 10: Dynamic Stop-Loss (V6.5) ──
        with _PhaseTimer("phase10_stoploss_ms", result["timings"]):
            sl_result = self._phase10_dynamic_stoploss(signal_result, market_data)
            result["phases"]["stoploss"] = sl_result

        # ── PHASE 11: Adaptive Take-Profit (V6.5) ──
        with _PhaseTimer("phase11_takeprofit_ms", result["timings"]):
            tp_result = self._phase11_adaptive_tp(signal_result, sl_result, market_data)
            result["phases"]["takeprofit"] = tp_result

        # ── PHASE 12: Diversification Check (V6.5) ──
        with _PhaseTimer("phase12_diversification_ms", result["timings"]):
            div_result = self._phase12_diversification(signal_result)
            result["phases"]["diversification"] = div_result

        if not div_result.get("diversified"):
            result["status"] = "DIVERSIFICATION_REJECTED"
            self._record_cycle(cycle_start, result)
            return result

        # ── PHASE 13: Execution ──
        with _PhaseTimer("phase13_execution_ms", result["timings"]):
            exec_result = self._phase13_execution(
                signal_result, risk_result, sl_result, tp_result, market_data,
                broker_client=broker_client, trading_mode=trading_mode,
            )
            result["phases"]["execution"] = exec_result

        # ── PHASE 14: Exit Management — runs every cycle (see Phase 0) ──

        if exec_result.get("trade_executed"):
            result["trade_executed"] = True
            result["status"] = "TRADE_EXECUTED"

            with _PhaseTimer("phase15_learning_ms", result["timings"]):
                self._phase15_learning(exec_result, signal_result)
        else:
            result["status"] = "EXECUTION_REJECTED"

        self._record_cycle(cycle_start, result)
        return result

    # ── Phase implementations ───────────────────────────────────────

    def _phase1_market_scan(self, market_data: Dict) -> Dict:
        # Use V6 MarketScanner when available
        if self.market_scanner:
            try:
                opportunities = self.market_scanner.scan_all_instruments(market_data)
                top = self.market_scanner.get_opportunities(top_n=5)
                return {
                    "total_scanned": len(market_data),
                    "filtered_count": len(opportunities),
                    "opportunities": top,
                    "scanner": "MarketScanner",
                }
            except Exception as e:
                logger.error("MarketScanner failed, falling back to inline scan: %s", e)

        # Fallback: inline scan (original logic)
        opportunities = []
        for symbol, data in market_data.items():
            spread = data.get("spread", 999)
            volume = data.get("volume", 0)
            if spread > 0.5 or volume < 100:
                continue
            vol_score = min(1.0, volume / 1000.0)
            spr_score = max(0.0, 1.0 - spread / 0.5)
            combined = (vol_score * 0.6) + (spr_score * 0.4)
            opportunities.append({"symbol": symbol, "data": data, "score": combined, "spread": spread, "volume": volume})
        opportunities.sort(key=lambda x: x["score"], reverse=True)
        return {"total_scanned": len(market_data), "filtered_count": len(opportunities), "opportunities": opportunities[:5], "scanner": "inline"}

    def _phase2_ai_analysis(self, market_data: Dict, scan_result: Dict) -> Dict:
        result = {"regime": "unknown", "predictions": {}}

        # Use V6 AIEngine when available
        if self.ai_engine:
            try:
                ai_pred = self.ai_engine.predict(
                    scan_result["opportunities"][0]["symbol"] if scan_result.get("opportunities") else "EURUSD",
                    market_data,
                )
                result["regime"] = ai_pred.get("regime", "unknown")
                if ai_pred.get("direction"):
                    result["predictions"][ai_pred.get("symbol", "unknown")] = {
                        "direction": ai_pred["direction"],
                        "confidence": ai_pred.get("confidence", 0.0),
                    }
                result["ai_engine"] = True
            except Exception as e:
                logger.error("AIEngine prediction failed: %s", e)

        # Use HMM regime detector as supplement
        if self.hmm_regime:
            try:
                for sym, data in market_data.items():
                    closes = data.get("closes", [])
                    if not closes:
                        candles = data.get("candles", [])
                        closes = [float(c.get("close", 0)) for c in candles] if candles else []
                    if len(closes) >= 20:
                        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] != 0 else 0
                                   for i in range(max(1, len(closes) - 20), len(closes))]
                        hmm_regime = self.hmm_regime.predict(returns)
                        if hmm_regime and hmm_regime != "UNKNOWN":
                            result["regime"] = hmm_regime
                            result["hmm_regime"] = True
                        break
            except Exception as e:
                logger.error("HMMRegimeDetector prediction failed: %s", e)

        # Fallback to existing regime detector + ensemble
        top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
        if top and self.regime_detector:
            try:
                candles = top["data"].get("candles", [])
                if candles and len(candles) >= 50:
                    import numpy as np
                    closes = [float(c.get("close", 0)) for c in candles[-50:]]
                    features = np.array(closes).reshape(1, -1)
                    pred = self.regime_detector.predict(features)
                    result["regime"] = pred.get("regime", "unknown") if isinstance(pred, dict) else str(pred)
            except Exception as e:
                logger.error("Regime detection failed: %s", e)

        if self.ensemble:
            for opp in scan_result.get("opportunities", []):
                try:
                    candles = opp["data"].get("candles", [])
                    if candles and len(candles) >= 60:
                        import asyncio
                        async def _predict(symbol=opp["symbol"]):
                            return await self.ensemble.predict(symbol=symbol, timeframe="M5", lookback=200)
                        pred = asyncio.run(_predict())
                        if pred and "error" not in pred:
                            result["predictions"][opp["symbol"]] = pred
                except Exception as e:
                    logger.error("Pipeline prediction failed for %s: %s", opp["symbol"], e)
        return result

    def _phase3_sentiment(self, scan_result: Dict) -> Dict:
        if not self.sentiment_analyzer:
            return {"available": False}
        top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
        if not top:
            return {"available": False}
        try:
            score = self.sentiment_analyzer.get_sentiment_score(top["symbol"])
            return {"available": True, **score}
        except Exception as e:
            logger.error("Sentiment analysis failed: %s", e)
            return {"available": False, "error": str(e)}

    def _phase4_news_strategy(self, scan_result: Dict) -> Dict:
        if not self.news_trader:
            return {"available": False, "strategy": "NORMAL"}
        top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
        if not top:
            return {"available": False, "strategy": "NORMAL"}
        try:
            return {"available": True, **self.news_trader.get_news_strategy(top["symbol"], datetime.now())}
        except Exception as e:
            logger.error("News strategy failed: %s", e)
            return {"available": False, "strategy": "NORMAL"}

    def _phase5_order_flow(self, scan_result: Dict, market_data: Dict) -> Dict:
        if not self.order_flow_analyzer:
            return {"available": False}
        top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
        if not top:
            return {"available": False}
        try:
            data = market_data.get(top["symbol"], {})
            return {"available": True, **self.order_flow_analyzer.analyze_order_flow(top["symbol"], data)}
        except Exception as e:
            logger.error("Order flow failed: %s", e)
            return {"available": False}

    def _phase6_pattern_recognition(self, scan_result: Dict) -> Dict:
        if not self.pattern_recognizer:
            return {"available": False}
        top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
        if not top:
            return {"available": False}
        try:
            import numpy as np
            candles = top["data"].get("candles", [])
            if candles and len(candles) >= 10:
                bars = np.array([[float(c.get("open", 0)), float(c.get("high", 0)),
                                  float(c.get("low", 0)), float(c.get("close", 0))] for c in candles])
                return {"available": True, **self.pattern_recognizer.recognize_pattern(bars)}
            return {"available": True, "signal": "NEUTRAL", "confidence": 0}
        except Exception as e:
            logger.error("Pattern recognition failed: %s", e)
            return {"available": False}

    def _phase7_multi_tf(self, scan_result: Dict, market_data: Dict) -> Dict:
        if not self.multi_tf_analyzer:
            return {"available": False}
        top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
        if not top:
            return {"available": False}
        try:
            data = market_data.get(top["symbol"], {})
            return {"available": True, **self.multi_tf_analyzer.analyze_all_timeframes(top["symbol"], data)}
        except Exception as e:
            logger.error("Multi-TF failed: %s", e)
            return {"available": False}

    def _phase8_signal_generation(self, scan_result, ai_result, sentiment_result, news_result,
                                   orderflow_result, pattern_result, tf_result) -> Dict:
        score = 0.0
        confidence = 0.0
        components_used = 0

        # Regime (10%)
        regime = ai_result.get("regime", "unknown")
        regime_scores = {"TRENDING": 0.3, "BREAKOUT": 0.2, "RANGING": -0.1, "VOLATILE": 0.0}
        score += regime_scores.get(regime, 0.0) * 0.10
        components_used += 1

        # Sentiment (15%)
        if sentiment_result.get("available"):
            s = sentiment_result.get("score", 0)
            score += s * 0.15
            confidence += sentiment_result.get("confidence", 0) * 0.15
            components_used += 1

        # News (10%)
        if news_result.get("available") and news_result.get("strategy") != "NORMAL":
            if news_result.get("action") == "TREND_FOLLOW":
                score += 0.2 * 0.10
            components_used += 1

        # Order flow (15%)
        if orderflow_result.get("available"):
            bias = orderflow_result.get("bias", 0)
            score += bias * 0.15
            confidence += orderflow_result.get("confidence", 0) * 0.15
            components_used += 1

        # Pattern (15%)
        if pattern_result.get("available") and pattern_result.get("signal") != "NEUTRAL":
            pscore = 1 if pattern_result["signal"] == "BUY" else -1
            score += pscore * pattern_result.get("confidence", 0) * 0.15
            confidence += pattern_result.get("confidence", 0) * 0.15
            components_used += 1

        # Strategy Diversification (10%) — uses existing strategy_diversification module
        if self.strategy_diversification:
            try:
                top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
                if top:
                    combined = self.strategy_diversification.get_signal_combined(top["data"])
                    if combined and combined.get("confidence", 0) > 0.5:
                        action_val = combined.get("action", "NEUTRAL")
                        if action_val != "NEUTRAL":
                            div_score = 1 if action_val == "BUY" else -1
                            score += div_score * combined["confidence"] * 0.10
                            confidence += combined["confidence"] * 0.10
                            components_used += 1
            except Exception:
                pass

        # Multi-TF (25%) — highest weight
        if tf_result.get("available") and tf_result.get("action") != "NEUTRAL":
            tfscore = 1 if tf_result["action"] == "BUY" else -1
            score += tfscore * tf_result.get("confidence", 0) * 0.25
            confidence += tf_result.get("confidence", 0) * 0.25
            components_used += 1

        # V6 strategy diversification fallback
        if abs(score) < 0.1 and self.strategy_diversification:
            top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
            if top:
                try:
                    combined = self.strategy_diversification.get_signal_combined(top["data"])
                    if combined and combined.get("confidence", 0) > 0.65:
                        action = "BUY" if combined.get("action", "BUY") == "BUY" else "SELL"
                        return {
                            "signal": {"symbol": top["symbol"], "action": action, "confidence": combined["confidence"],
                                       "entry_price": top["data"].get("current_price", 0), "stop_loss": 0, "take_profit": 0},
                            "strategy": "diversified", "confidence": combined["confidence"],
                        }
                except Exception:
                    pass

        # Ensemble fallback
        if abs(score) < 0.1:
            for sym, pred in ai_result.get("predictions", {}).items():
                conf = pred.get("confidence", 0)
                if conf > 0.70:
                    direction_val = pred.get("direction", 1.0)
                    action = "BUY" if (isinstance(direction_val, (int, float)) and direction_val > 0) else "SELL"
                    top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
                    return {
                        "signal": {"symbol": sym, "action": action, "confidence": conf,
                                   "entry_price": pred.get("entry_price", top["data"].get("current_price", 0) if top else 0),
                                   "stop_loss": pred.get("stop_loss", 0), "take_profit": pred.get("take_profit", 0)},
                        "strategy": "ensemble", "confidence": conf,
                    }
            return {"signal": None}

        # Get optimized confidence threshold
        min_conf = 0.65
        if self.optimizer:
            min_conf = self.optimizer.get_parameters().get("confidence_threshold", 0.65)

        if confidence / max(components_used, 1) < min_conf:
            return {"signal": None}

        if score > 0.3:
            action = "BUY"
        elif score < -0.3:
            action = "SELL"
        else:
            return {"signal": None}

        top = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
        return {
            "signal": {"symbol": top["symbol"], "action": action, "confidence": confidence / max(components_used, 1),
                       "entry_price": top["data"].get("current_price", 0), "stop_loss": 0, "take_profit": 0},
            "strategy": "v65_combined", "confidence": confidence / max(components_used, 1),
            "score": score, "components_used": components_used,
        }

    # ── Helper methods for dynamic risk parameters ───────────────────

    def _get_account_balance(self):
        """Fetch real account balance from MT5."""
        try:
            from mcp_integration.services import MT5Service
            service = MT5Service()
            loop = asyncio.new_event_loop()
            try:
                info = loop.run_until_complete(service.get_account_info())
                return info.get("balance", 10000.0)
            finally:
                loop.close()
        except Exception:
            return 10000.0

    def _get_current_drawdown(self):
        """Get current drawdown from DrawdownMonitor (as decimal)."""
        try:
            from risk_management.models import DrawdownMonitor
            monitor = DrawdownMonitor.objects.filter(user_id=1).first()
            if monitor:
                return monitor.current_drawdown / 100.0  # Convert percentage to decimal
        except Exception:
            pass
        return 0.02

    def _phase9_risk_management(self, signal_result: Dict, market_data: Dict) -> Dict:
        signal = signal_result.get("signal", {})
        symbol = signal.get("symbol", "")

        # ── FIX 1: DrawdownMonitor circuit-breaker check ──────────────
        try:
            from risk_management.models import DrawdownMonitor
            monitor, _ = DrawdownMonitor.objects.get_or_create(user_id=1)
            if monitor.is_circuit_breaker_triggered:
                logger.warning("Circuit breaker triggered (tier %s) — rejecting trade", monitor.current_tier)
                return {"approved": False, "reason": "Circuit breaker triggered", "tier": monitor.current_tier}
        except Exception as e:
            logger.debug("DrawdownMonitor unavailable: %s", e)

        # ── FIX 1b: Daily performance limit check ─────────────────────
        try:
            from risk_management.models import DailyPerformance
            from datetime import date as _date
            daily = DailyPerformance.objects.filter(user_id=1, date=_date.today()).first()
            if daily and daily.total_pnl < -(daily.starting_balance * 0.02):  # 2% daily loss limit
                logger.warning("Daily loss limit reached: pnl=%.2f vs limit=%.2f",
                               daily.total_pnl, -(daily.starting_balance * 0.02))
                return {"approved": False, "reason": "Daily loss limit reached"}
        except Exception as e:
            logger.debug("DailyPerformance unavailable: %s", e)

        # ── FIX 1c: Enforce 4-tier circuit breaker size reduction ─────
        size_multiplier = 1.0
        try:
            from risk_management.models import DrawdownMonitor
            monitor = DrawdownMonitor.objects.filter(user_id=1).first()
            if monitor:
                tier = monitor.get_drawdown_recovery_tier()
                size_multiplier = {0: 1.0, 1: 0.5, 2: 0.25, 3: 0.0, 4: 0.0}.get(tier, 1.0)
        except Exception:
            pass

        # ── FIX 2: Dynamic risk parameters (replaces hardcoded values) ─
        if self.risk_sizer:
            conf = signal.get("confidence", 0.7)
            vol = market_data.get(symbol, {}).get("volatility_ratio", 1.0)

            # Real account balance from MT5 or DB
            account_balance = self._get_account_balance()

            # Real current drawdown from DrawdownMonitor
            current_drawdown = self._get_current_drawdown()

            # Real correlation with existing positions
            avg_correlation = 0.0
            if self.open_positions and self.diversification:
                try:
                    correlations = []
                    for pos in self.open_positions:
                        corr_val = abs(self.diversification.get_correlation(symbol, pos["symbol"]))
                        correlations.append(corr_val)
                    avg_correlation = sum(correlations) / len(correlations) if correlations else 0.0
                except Exception:
                    pass

            # Use regime from Phase 2, not hardcoded
            regime = signal_result.get("regime", "NORMAL")
            if regime == "unknown":
                regime = "NORMAL"

            risk_pct = self.risk_sizer.calculate_optimal_risk(
                account_balance, conf, vol, avg_correlation, current_drawdown, regime,
            )
        else:
            risk_pct = 0.01

        base_size = 0.01 * (risk_pct / 0.005)

        # Apply circuit breaker size reduction
        base_size *= size_multiplier

        if self.dynamic_kelly:
            try:
                kelly_mult = self.dynamic_kelly.get_position_size_multiplier()
                base_size *= kelly_mult
            except Exception:
                pass

        if self.correlation_manager:
            try:
                base_size = self.correlation_manager.get_adjusted_position_size(symbol, base_size)
            except Exception:
                pass

        if self.volatility_scaler and symbol in market_data:
            try:
                d = market_data[symbol]
                cur_atr = d.get("current_atr", 0)
                hist_atr = d.get("historical_atr", 1)
                if hist_atr > 0:
                    vscale = self.volatility_scaler.get_volatility_scale(symbol, cur_atr, hist_atr)
                    base_size *= vscale
            except Exception:
                pass

        base_size = max(0.001, min(0.02, base_size))
        return {"approved": True, "position_size": base_size, "adjusted_size": base_size, "risk_pct": risk_pct}

    def _phase10_dynamic_stoploss(self, signal_result: Dict, market_data: Dict) -> Dict:
        if not self.dynamic_stop_loss:
            signal = signal_result.get("signal", {})
            entry = signal.get("entry_price", 0)
            direction = signal.get("action", "BUY")
            sl = entry - 0.002 if direction == "BUY" else entry + 0.002
            return {"stop_loss": sl, "distance": 0.002, "distance_pips": 20, "method": "DEFAULT"}

        signal = signal_result.get("signal", {})
        symbol = signal.get("symbol", "")
        data = market_data.get(symbol, {})
        return self.dynamic_stop_loss.calculate_optimal_stop(symbol, signal.get("entry_price", 0), signal.get("action", "BUY"), data)

    def _phase11_adaptive_tp(self, signal_result: Dict, sl_result: Dict, market_data: Dict) -> Dict:
        if not self.adaptive_tp:
            signal = signal_result.get("signal", {})
            entry = signal.get("entry_price", 0)
            direction = signal.get("action", "BUY")
            dist = abs(entry - sl_result.get("stop_loss", entry - 0.002)) * 2
            tp = entry + dist if direction == "BUY" else entry - dist
            return {"tp1": tp, "tp2": tp, "tp3": tp, "distance": dist, "distance_pips": dist * 10000, "rr_ratio": 2.0, "method": "DEFAULT"}

        signal = signal_result.get("signal", {})
        symbol = signal.get("symbol", "")
        data = market_data.get(symbol, {})
        return self.adaptive_tp.calculate_take_profit(signal.get("entry_price", 0), signal.get("action", "BUY"),
                                                       sl_result.get("stop_loss", 0), data)

    def _phase12_diversification(self, signal_result: Dict) -> Dict:
        if not self.diversification:
            return {"diversified": True, "reason": "No diversification module", "action": "ACCEPT", "penalty": 1.0}
        signal = signal_result.get("signal", {})
        return self.diversification.check_diversification(signal.get("symbol", ""), self.open_positions)

    def _phase13_execution(self, signal_result, risk_result, sl_result, tp_result, market_data,
                           broker_client=None, trading_mode: str = "semi") -> Dict:
        result = {"trade_executed": False, "order_details": None, "reject_reason": None, "trading_mode": trading_mode}
        signal = signal_result.get("signal", {})
        symbol = signal.get("symbol", "")

        if self.execution_optimizer and symbol in market_data:
            try:
                data = market_data[symbol]
                spread_check = self.execution_optimizer.check_spread(data.get("spread", 0), symbol)
                if not spread_check.get("acceptable", True):
                    result["reject_reason"] = "SPREAD_TOO_HIGH"
                    return result
            except Exception:
                pass

        volume = risk_result.get("adjusted_size", 0.01)
        action = signal.get("action", "BUY")
        sl = sl_result.get("stop_loss", 0)
        tp = tp_result.get("tp1", 0)

        result["order_details"] = {
            "symbol": symbol, "action": action, "volume": float(volume) if volume else 0.01,
            "stop_loss": float(sl) if sl else 0, "take_profit": float(tp) if tp else 0,
            "strategy": signal_result.get("strategy", "v65"), "confidence": signal_result.get("confidence", 0),
        }

        if trading_mode == "manual":
            result["reject_reason"] = "MANUAL_MODE"
            return result
        if trading_mode == "semi":
            result["pending_approval"] = True
            # Resolve entry price from signal or market data
            resolved_entry = signal.get("entry_price", 0.0)
            if resolved_entry <= 0 and symbol in market_data:
                resolved_entry = market_data[symbol].get("current_price", 0.0)
            # Still track as an open position for diversification (pending state)
            self._add_open_position(symbol, action, float(sl) if sl else 0,
                                    float(tp) if tp else 0, float(volume) if volume else 0.01,
                                    signal_result.get("strategy", "v65"),
                                    entry_price=resolved_entry,
                                    tp2=float(tp_result.get("tp2", 0)) if tp_result.get("tp2") else 0.0,
                                    tp3=float(tp_result.get("tp3", 0)) if tp_result.get("tp3") else 0.0)
            return result

        if broker_client is None:
            result["reject_reason"] = "NO_BROKER_CLIENT"
            return result

        try:
            position_type = "BUY" if action.upper() in ("BUY", "LONG") else "SELL"
            import asyncio
            async def _open_position():
                return await broker_client.open_position(
                    symbol=symbol, volume=float(volume) if volume else 0.01,
                    position_type=position_type, stop_loss=float(sl) if sl else 0.0,
                    take_profit=float(tp) if tp else 0.0, magic=123456,
                    comment=f"V6.5-{signal_result.get('strategy', 'ai')}",
                )
            resp = asyncio.run(_open_position())
            if resp and resp.success:
                result["trade_executed"] = True
                result["broker_response"] = resp.data
                result["status"] = "EXECUTED"
                # Resolve entry price from signal or market data
                resolved_entry = signal.get("entry_price", 0.0)
                if resolved_entry <= 0 and symbol in market_data:
                    resolved_entry = market_data[symbol].get("current_price", 0.0)
                # Track the open position for diversification & exit management
                self._add_open_position(symbol, action, float(sl) if sl else 0,
                                        float(tp) if tp else 0, float(volume) if volume else 0.01,
                                        signal_result.get("strategy", "v65"),
                                        entry_price=resolved_entry,
                                        tp2=float(tp_result.get("tp2", 0)) if tp_result.get("tp2") else 0.0,
                                        tp3=float(tp_result.get("tp3", 0)) if tp_result.get("tp3") else 0.0)
            else:
                result["reject_reason"] = f"BROKER_REJECTED: {resp.error if resp else 'no response'}"
        except Exception as e:
            result["reject_reason"] = f"BROKER_ERROR: {e}"
            logger.error("V6.5 broker execution failed: %s", e, exc_info=True)
        return result

    def _add_open_position(self, symbol: str, action: str, stop_loss: float,
                           take_profit: float, volume: float, strategy: str,
                           entry_price: float = 0.0, tp2: float = 0.0, tp3: float = 0.0):
        """Add a tracked position to the open positions list.

        ``entry_price`` should be filled from the current market data at the
        time the trade is recorded.  The caller (Phase 13) is responsible for
        resolving it from ``market_data[symbol]['current_price']``.

        ``tp2`` and ``tp3`` store all take-profit levels for partial-close
        logic in Phase 14.
        """
        position = {
            "symbol": symbol,
            "direction": action.upper(),
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "tp1": take_profit,
            "tp2": tp2,
            "tp3": tp3,
            "volume": volume,
            "strategy": strategy,
            "entry_time": datetime.now().isoformat(),
            "status": "OPEN",
            "tp1_closed": False,
            "tp2_closed": False,
            "tp3_closed": False,
        }
        self.open_positions.append(position)
        logger.info("Position tracked: %s %s @ %.5f (SL=%.5f, TP1=%.5f, TP2=%.5f, TP3=%.5f) — %d open",
                     action, symbol, entry_price, stop_loss, take_profit, tp2, tp3,
                     len(self.open_positions))

    def _remove_position(self, position: Dict, exit_reason: str, exit_price: float = 0.0):
        """Remove a position from open tracking and optionally trigger learning."""
        position["status"] = "CLOSED"
        position["exit_reason"] = exit_reason
        position["exit_time"] = datetime.now().isoformat()
        position["exit_price"] = exit_price
        if position in self.open_positions:
            self.open_positions.remove(position)
        logger.info("Position closed: %s %s — reason=%s, %d remaining",
                     position.get("direction", ""), position.get("symbol", ""),
                     exit_reason, len(self.open_positions))

    def _phase14_exit_management(self, exec_result: Dict, market_data: Dict):
        """Manage exits: trailing stops, partial closes, SL/TP hits, time exits.

        Uses ``market_data`` to obtain the current price for each tracked
        symbol and evaluates whether stop-loss, take-profit, trailing stops,
        partial closes, or time-based exit conditions have been met.  Closed
        positions are removed from ``self.open_positions`` and fed back to
        the self-optimizer for continuous learning.
        """
        closed_symbols = []
        for position in list(self.open_positions):  # Iterate copy for safe removal
            symbol = position.get("symbol", "")
            direction = position.get("direction", "BUY")
            entry_price = position.get("entry_price", 0.0)
            stop_loss = position.get("stop_loss", 0.0)
            entry_time_str = position.get("entry_time", "")

            # Resolve current price from market data
            current_price = 0.0
            sym_data = market_data.get(symbol, {})
            if sym_data:
                current_price = sym_data.get("current_price", 0.0)
                # Also try to use the latest candle close if available
                candles = sym_data.get("candles", [])
                if candles and isinstance(candles, list) and len(candles) > 0:
                    last_close = float(candles[-1].get("close", 0))
                    if last_close > 0:
                        current_price = last_close

            if current_price <= 0 or entry_price <= 0:
                continue  # Can't evaluate without valid prices

            # ── 1. TRAILING STOP LOGIC ───────────────────────────────
            if direction == "BUY":
                profit_pips = (current_price - entry_price) * 10000
                if profit_pips >= 5:  # Only trail after 5 pips profit
                    if profit_pips < 10:
                        trail_distance = 0.0005  # 5 pips
                    elif profit_pips < 20:
                        trail_distance = 0.0010  # 10 pips
                    elif profit_pips < 50:
                        trail_distance = 0.0015  # 15 pips
                    else:
                        trail_distance = 0.0020  # 20 pips

                    new_stop = current_price - trail_distance
                    if new_stop > stop_loss:
                        position["stop_loss"] = new_stop
                        stop_loss = new_stop  # Update local reference
                        logger.info("Trailing stop moved UP to %.5f for %s", new_stop, symbol)
            else:  # SELL
                profit_pips = (entry_price - current_price) * 10000
                if profit_pips >= 5:
                    if profit_pips < 10:
                        trail_distance = 0.0005
                    elif profit_pips < 20:
                        trail_distance = 0.0010
                    elif profit_pips < 50:
                        trail_distance = 0.0015
                    else:
                        trail_distance = 0.0020

                    new_stop = current_price + trail_distance
                    if new_stop < stop_loss or stop_loss == 0:
                        position["stop_loss"] = new_stop
                        stop_loss = new_stop
                        logger.info("Trailing stop moved DOWN to %.5f for %s", new_stop, symbol)

            # ── 2. BREAKEVEN STOP ────────────────────────────────────
            if direction == "BUY" and (current_price - entry_price) * 10000 >= 5:
                if stop_loss < entry_price:
                    position["stop_loss"] = entry_price + 0.0001  # Breakeven + 1 pip
                    stop_loss = entry_price + 0.0001
                    logger.info("Breakeven stop set for %s", symbol)
            elif direction == "SELL" and (entry_price - current_price) * 10000 >= 5:
                if stop_loss > entry_price or stop_loss == 0:
                    position["stop_loss"] = entry_price - 0.0001
                    stop_loss = entry_price - 0.0001
                    logger.info("Breakeven stop set for %s", symbol)

            # ── 3. PARTIAL CLOSES AT TP LEVELS ───────────────────────
            tp1 = position.get("tp1", 0)
            tp2 = position.get("tp2", 0)
            tp3 = position.get("tp3", 0)

            if direction == "BUY":
                if not position.get("tp1_closed") and tp1 > 0 and current_price >= tp1:
                    close_volume = position["volume"] * 0.40  # Close 40%
                    position["volume"] *= 0.60
                    position["tp1_closed"] = True
                    position["stop_loss"] = entry_price + 0.0001  # Move to breakeven
                    stop_loss = entry_price + 0.0001
                    logger.info("TP1 hit: closed 40%% of %s, breakeven set (vol=%.4f)", symbol, close_volume)

                if not position.get("tp2_closed") and tp2 > 0 and current_price >= tp2:
                    close_volume = position["volume"] * 0.50  # Close 50% of remaining
                    position["volume"] *= 0.50
                    position["tp2_closed"] = True
                    logger.info("TP2 hit: closed 50%% of remaining %s (vol=%.4f)", symbol, close_volume)

                if not position.get("tp3_closed") and tp3 > 0 and current_price >= tp3:
                    exit_price = current_price if current_price > 0 else entry_price
                    self._close_position(position, "TP3_FULL", exit_price)
                    closed_symbols.append(symbol)
                    continue
            else:  # SELL
                if not position.get("tp1_closed") and tp1 > 0 and current_price <= tp1:
                    close_volume = position["volume"] * 0.40
                    position["volume"] *= 0.60
                    position["tp1_closed"] = True
                    position["stop_loss"] = entry_price - 0.0001
                    stop_loss = entry_price - 0.0001
                    logger.info("TP1 hit: closed 40%% of %s, breakeven set (vol=%.4f)", symbol, close_volume)

                if not position.get("tp2_closed") and tp2 > 0 and current_price <= tp2:
                    close_volume = position["volume"] * 0.50
                    position["volume"] *= 0.50
                    position["tp2_closed"] = True
                    logger.info("TP2 hit: closed 50%% of remaining %s (vol=%.4f)", symbol, close_volume)

                if not position.get("tp3_closed") and tp3 > 0 and current_price <= tp3:
                    exit_price = current_price if current_price > 0 else entry_price
                    self._close_position(position, "TP3_FULL", exit_price)
                    closed_symbols.append(symbol)
                    continue

            # ── 4. STOP LOSS HIT DETECTION ───────────────────────────
            if direction == "BUY" and current_price <= stop_loss and stop_loss > 0:
                logger.info("Stop-loss hit for %s %s @ %.5f (SL=%.5f)",
                            direction, symbol, current_price, stop_loss)
                self._close_position(position, "STOP_LOSS", current_price)
                closed_symbols.append(symbol)
            elif direction == "SELL" and current_price >= stop_loss and stop_loss > 0:
                logger.info("Stop-loss hit for %s %s @ %.5f (SL=%.5f)",
                            direction, symbol, current_price, stop_loss)
                self._close_position(position, "STOP_LOSS", current_price)
                closed_symbols.append(symbol)

            # ── 5. TIME-BASED EXIT (48 hours) ────────────────────────
            if entry_time_str:
                try:
                    entry_time = datetime.fromisoformat(entry_time_str)
                    hours_held = (datetime.now() - entry_time).total_seconds() / 3600
                    if hours_held > 48:
                        logger.info("Time-based exit for %s after %.1f hours",
                                    symbol, hours_held)
                        exit_price = current_price if current_price > 0 else entry_price
                        self._close_position(position, "TIME_EXIT", exit_price)
                        closed_symbols.append(symbol)
                except (ValueError, TypeError):
                    pass

        if closed_symbols:
            logger.info("Phase 14 closed %d position(s): %s",
                        len(closed_symbols), ", ".join(closed_symbols))

        # ── Original time_based_exit module hook (if available) ─────────
        if self.time_based_exit:
            order = exec_result.get("order_details", {})
            logger.info("Trade registered for exit management: %s %s",
                        order.get("action"), order.get("symbol"))

    def _close_position(self, position: Dict, exit_reason: str, exit_price: float):
        """Close a position, remove from tracking, and trigger learning.

        Computes a rough PnL from entry_price vs exit_price and passes the
        result to the self-optimizer so it can learn from wins and losses.
        """
        entry_price = position.get("entry_price", 0.0)
        direction = position.get("direction", "BUY")
        volume = position.get("volume", 0.01)
        multiplier = 100000.0  # Standard lot multiplier for forex

        if entry_price > 0 and exit_price > 0:
            direction_sign = 1 if direction == "BUY" else -1
            pnl_pips = (exit_price - entry_price) * direction_sign * multiplier
        else:
            pnl_pips = 0.0

        trade_result = {
            "symbol": position.get("symbol", ""),
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "volume": volume,
            "pnl_pips": round(pnl_pips, 2),
            "profit": pnl_pips * volume,  # Approximate monetary profit
            "strategy": position.get("strategy", ""),
        }

        self._remove_position(position, exit_reason, exit_price)
        self._closed_this_cycle = True  # FIX 6: flag for learning trigger

        # Feed result back to the self-optimizer for continuous learning
        if self.optimizer:
            try:
                self.optimizer.update_from_trade(trade_result)
                logger.info("Self-optimizer updated from %s trade: pnl=%.2f pips",
                            exit_reason, pnl_pips)
            except Exception as e:
                logger.error("Self-optimizer update failed: %s", e)

    def _phase15_learning(self, exec_result: Dict, signal_result: Dict):
        # Update AIEngine from trade results
        if self.ai_engine:
            try:
                self.ai_engine.update_from_trade({
                    "symbol": exec_result.get("order_details", {}).get("symbol", ""),
                    "strategy": signal_result.get("strategy", ""),
                    "confidence": signal_result.get("confidence", 0),
                    "regime": signal_result.get("regime", "unknown"),
                    "profit": 0,
                })
            except Exception:
                pass

        if self.dynamic_kelly:
            try:
                self.dynamic_kelly.update_stats({"profit": 0, "symbol": exec_result.get("order_details", {}).get("symbol", "")})
            except Exception:
                pass
        if self.transfer_learning:
            try:
                self.transfer_learning.fine_tune_model("ensemble", {
                    "symbol": exec_result.get("order_details", {}).get("symbol", ""),
                    "strategy": signal_result.get("strategy", ""),
                    "confidence": signal_result.get("confidence", 0),
                })
            except Exception:
                pass
        if self.optimizer:
            try:
                self.optimizer.update_from_trade(exec_result.get("order_details", {}))
            except Exception:
                pass

    def _record_cycle(self, cycle_start: float, result: Dict):
        duration = (time.perf_counter() - cycle_start) * 1000
        self._cycle_count += 1
        self._total_cycle_time_ms += duration
        self._last_phase_timings = result.get("timings", {})
        result["cycle_duration_ms"] = round(duration, 2)
        logger.info("V6.5 cycle #%d complete in %.2fms: status=%s, trade=%s",
                     self._cycle_count, duration, result.get("status"), result.get("trade_executed"))

    def get_status(self) -> Dict:
        return {
            "version": "6.5", "initialized": self._initialized, "component_count": self.component_count,
            "total_components": 22, "performance": {
                "total_cycles": self._cycle_count,
                "avg_cycle_time_ms": round(self._total_cycle_time_ms / self._cycle_count, 2) if self._cycle_count > 0 else 0,
                "last_cycle_timings": self._last_phase_timings,
            },
            "open_positions_count": len(self.open_positions),
            "component_health": self._component_health.copy(),
        }


_v65_orchestrator: Optional[V65TradingOrchestrator] = None


def get_v65_orchestrator() -> V65TradingOrchestrator:
    global _v65_orchestrator
    if _v65_orchestrator is None:
        _v65_orchestrator = V65TradingOrchestrator()
    return _v65_orchestrator
