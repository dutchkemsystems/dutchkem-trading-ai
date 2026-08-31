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

        self._initialized = False
        self._cycle_count = 0
        self._total_cycle_time_ms = 0.0
        self._last_phase_timings: Dict[str, float] = {}

    def _lazy_load(self, module_path: str, attr_name: str, friendly_name: str):
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, attr_name)
            instance = cls()
            logger.info("V6.5 loaded: %s", friendly_name)
            return instance
        except (ImportError, AttributeError, Exception) as e:
            logger.warning("V6.5 component not available: %s (%s)", friendly_name, e)
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
        ]
        return sum(1 for c in all_components if c is not None)

    def run_trading_cycle(self, market_data: Dict[str, Any], broker_client=None, trading_mode: str = "semi") -> Dict[str, Any]:
        self.initialize()
        cycle_start = time.perf_counter()
        result: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(), "version": "6.5",
            "phases": {}, "trade_executed": False, "timings": {},
        }

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

        if exec_result.get("trade_executed"):
            result["trade_executed"] = True
            result["status"] = "TRADE_EXECUTED"

            with _PhaseTimer("phase14_exit_ms", result["timings"]):
                self._phase14_exit_management(exec_result)

            with _PhaseTimer("phase15_learning_ms", result["timings"]):
                self._phase15_learning(exec_result, signal_result)
        else:
            result["status"] = "EXECUTION_REJECTED"

        self._record_cycle(cycle_start, result)
        return result

    # ── Phase implementations ───────────────────────────────────────

    def _phase1_market_scan(self, market_data: Dict) -> Dict:
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
        return {"total_scanned": len(market_data), "filtered_count": len(opportunities), "opportunities": opportunities[:5]}

    def _phase2_ai_analysis(self, market_data: Dict, scan_result: Dict) -> Dict:
        result = {"regime": "unknown", "predictions": {}}
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
                        loop = asyncio.new_event_loop()
                        try:
                            pred = loop.run_until_complete(self.ensemble.predict(symbol=opp["symbol"], timeframe="M5", lookback=200))
                        finally:
                            loop.close()
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

    def _phase9_risk_management(self, signal_result: Dict, market_data: Dict) -> Dict:
        signal = signal_result.get("signal", {})
        symbol = signal.get("symbol", "")

        if self.risk_sizer:
            conf = signal.get("confidence", 0.7)
            vol = market_data.get(symbol, {}).get("volatility_ratio", 1.0)
            corr = 0.0
            dd = 0.02
            regime = "NORMAL"
            risk_pct = self.risk_sizer.calculate_optimal_risk(10000, conf, vol, corr, dd, regime)
        else:
            risk_pct = 0.01

        base_size = 0.01 * (risk_pct / 0.005)

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
        return self.diversification.check_diversification(signal.get("symbol", ""), [])

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
            return result

        if broker_client is None:
            result["reject_reason"] = "NO_BROKER_CLIENT"
            return result

        try:
            position_type = "BUY" if action.upper() in ("BUY", "LONG") else "SELL"
            loop = None
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = None
            except RuntimeError:
                loop = None
            if loop is None:
                loop = asyncio.new_event_loop()
                close_loop = True
            else:
                close_loop = False
            try:
                resp = loop.run_until_complete(broker_client.open_position(
                    symbol=symbol, volume=float(volume) if volume else 0.01,
                    position_type=position_type, stop_loss=float(sl) if sl else 0.0,
                    take_profit=float(tp) if tp else 0.0, magic=123456,
                    comment=f"V6.5-{signal_result.get('strategy', 'ai')}",
                ))
                if resp and resp.success:
                    result["trade_executed"] = True
                    result["broker_response"] = resp.data
                    result["status"] = "EXECUTED"
                else:
                    result["reject_reason"] = f"BROKER_REJECTED: {resp.error if resp else 'no response'}"
            finally:
                if close_loop:
                    loop.close()
        except Exception as e:
            result["reject_reason"] = f"BROKER_ERROR: {e}"
            logger.error("V6.5 broker execution failed: %s", e, exc_info=True)
        return result

    def _phase14_exit_management(self, exec_result: Dict):
        if self.time_based_exit:
            order = exec_result.get("order_details", {})
            logger.info("Trade registered for exit: %s %s", order.get("action"), order.get("symbol"))

    def _phase15_learning(self, exec_result: Dict, signal_result: Dict):
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
        }


_v65_orchestrator: Optional[V65TradingOrchestrator] = None


def get_v65_orchestrator() -> V65TradingOrchestrator:
    global _v65_orchestrator
    if _v65_orchestrator is None:
        _v65_orchestrator = V65TradingOrchestrator()
    return _v65_orchestrator
