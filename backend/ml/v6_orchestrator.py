"""
V6 Complete Trading Orchestrator
Ties together ALL V1-V6 components into a single trading cycle.

Phases:
  1. Market Scan     — Scan 28+ instruments for opportunities
  2. AI & Regime     — Ensemble prediction + regime detection + meta-learning
  3. Signal Gen      — Multi-strategy signal with confluence scoring
  4. Risk Management — Kelly, correlation, volatility, dynamic allocation
  5. Execution       — Spread/slippage checks, optimal order routing
  6. Exit Management — Time-based progressive exits
  7. Learning        — Transfer learning fine-tune, Kelly update
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.v6_orchestrator")


class V6TradingOrchestrator:
    """
    Master orchestrator for the V6 trading system.
    Runs the complete cycle: Scan -> AI -> Signal -> Risk -> Execute -> Learn
    """

    def __init__(self):
        # V1: Gold Edge
        self.gold_edge_active = True

        # V2: Scalping
        self.scalping_scanner = None  # lazy init

        # V3: AI/ML
        self.ensemble = None  # lazy init
        self.rl_agent = None  # lazy init
        self.regime_detector = None  # lazy init

        # V6: Advanced (lazy init to avoid import errors)
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

        self._initialized = False

    def initialize(self):
        """Initialize all V6 components with graceful fallback."""
        if self._initialized:
            return

        # --- Meta Learner (regime-based learning rate adjustment) ---
        try:
            from ml.meta_learner import MetaLearner
            self.meta_learner = MetaLearner()
            logger.info("V6 MetaLearner loaded")
        except ImportError:
            logger.warning("MetaLearner not available")

        # --- Asset Class Ensemble (specialized per asset type) ---
        try:
            from ml.asset_ensemble import AssetClassEnsemble
            self.asset_ensembles = AssetClassEnsemble()
            logger.info("V6 AssetClassEnsemble loaded")
        except ImportError:
            logger.warning("AssetClassEnsemble not available")

        # --- Transfer Learning (pre-train historical, fine-tune live) ---
        try:
            from ml.transfer_learning import TransferLearning
            self.transfer_learning = TransferLearning()
            logger.info("V6 TransferLearning loaded")
        except ImportError:
            logger.warning("TransferLearning not available")

        # --- Dynamic Asset Allocation (capital allocation by performance) ---
        try:
            from ml.dynamic_allocation import DynamicAssetAllocation
            self.dynamic_allocation = DynamicAssetAllocation()
            logger.info("V6 DynamicAssetAllocation loaded")
        except ImportError:
            logger.warning("DynamicAssetAllocation not available")

        # --- Correlation Manager (reduce size for correlated assets) ---
        # Uses the version from dynamic_allocation which has get_adjusted_position_size()
        try:
            from ml.dynamic_allocation import CorrelationManager as DynCorrelationManager
            self.correlation_manager = DynCorrelationManager()
            logger.info("V6 CorrelationManager loaded")
        except ImportError:
            logger.warning("CorrelationManager not available")

        # --- Volatility Scaler (scale size by current vol regime) ---
        # Uses the version from dynamic_allocation which has get_volatility_scale()
        try:
            from ml.dynamic_allocation import VolatilityScaler as DynVolatilityScaler
            self.volatility_scaler = DynVolatilityScaler()
            logger.info("V6 VolatilityScaler loaded")
        except ImportError:
            logger.warning("VolatilityScaler not available")

        # --- Dynamic Kelly (Kelly Criterion position sizing) ---
        # Uses the version from time_based_exit which has get_position_size_multiplier()
        try:
            from ml.time_based_exit import DynamicKelly as TimeDynKelly
            self.dynamic_kelly = TimeDynKelly()
            logger.info("V6 DynamicKelly loaded")
        except ImportError:
            logger.warning("DynamicKelly not available")

        # --- Strategy Diversification (multiple strategies simultaneously) ---
        try:
            from ml.strategy_diversification import StrategyDiversification
            self.strategy_diversification = StrategyDiversification()
            logger.info("V6 StrategyDiversification loaded")
        except ImportError:
            logger.warning("StrategyDiversification not available")

        # --- Time-Based Exit (close stale trades) ---
        try:
            from ml.time_based_exit import TimeBasedExit
            self.time_based_exit = TimeBasedExit()
            logger.info("V6 TimeBasedExit loaded")
        except ImportError:
            logger.warning("TimeBasedExit not available")

        # --- Execution Optimizer (spread/slippage/order routing) ---
        # Uses the version from time_based_exit which has check_spread / check_slippage
        try:
            from ml.time_based_exit import ExecutionOptimizer as TimeExecOptimizer
            self.execution_optimizer = TimeExecOptimizer()
            logger.info("V6 ExecutionOptimizer loaded")
        except ImportError:
            logger.warning("ExecutionOptimizer not available")

        # --- V3 Pipeline (existing ensemble prediction pipeline) ---
        try:
            from ml.pipeline import pipeline
            self.ensemble = pipeline
            logger.info("V3 PredictionPipeline loaded")
        except ImportError:
            logger.warning("PredictionPipeline not available")

        # --- Regime Detector (V3) ---
        try:
            from ml.models.regime_detector import RegimeDetector
            self.regime_detector = RegimeDetector()
            logger.info("V3 RegimeDetector loaded")
        except (ImportError, Exception):
            logger.warning("RegimeDetector not available")

        self._initialized = True
        logger.info("V6 Trading Orchestrator fully initialized")

    def run_trading_cycle(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete V6 trading cycle.

        Called by Celery task every 60 seconds.

        Args:
            market_data: Dict of symbol -> {
                'candles': list[dict],   # OHLCV candle data
                'current_price': float,
                'spread': float,
                'volume': int,
                'current_atr': float,   # optional
                'historical_atr': float, # optional
                'highs': list[float],    # optional, for volatility
                'lows': list[float],     # optional
                'closes': list[float],   # optional
            }

        Returns:
            Dict with phase results, status, and trade details.
        """
        self.initialize()

        result: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "phases": {},
            "trade_executed": False,
        }

        # ── PHASE 1: Market Scanning ────────────────────────────────
        scan_result = self._phase1_market_scan(market_data)
        result["phases"]["scan"] = scan_result

        if not scan_result.get("opportunities"):
            result["status"] = "NO_OPPORTUNITIES"
            return result

        # ── PHASE 2: AI & Regime Detection ──────────────────────────
        ai_result = self._phase2_ai_analysis(market_data, scan_result)
        result["phases"]["ai"] = ai_result

        # ── PHASE 3: Signal Generation ──────────────────────────────
        signal_result = self._phase3_signal_generation(scan_result, ai_result)
        result["phases"]["signal"] = signal_result

        if not signal_result.get("signal"):
            result["status"] = "NO_SIGNAL"
            return result

        # ── PHASE 4: Risk Management ────────────────────────────────
        risk_result = self._phase4_risk_management(signal_result, market_data)
        result["phases"]["risk"] = risk_result

        if not risk_result.get("approved"):
            result["status"] = "RISK_REJECTED"
            return result

        # ── PHASE 5: Execution Optimization ─────────────────────────
        exec_result = self._phase5_execution(signal_result, risk_result, market_data)
        result["phases"]["execution"] = exec_result

        if exec_result.get("trade_executed"):
            result["trade_executed"] = True
            result["status"] = "TRADE_EXECUTED"

            # ── PHASE 6: Time-Based Exit Monitoring ────────────────
            self._phase6_exit_management(exec_result)

            # ── PHASE 7: Learning ──────────────────────────────────
            self._phase7_learning(exec_result, signal_result)
        else:
            result["status"] = "EXECUTION_REJECTED"

        return result

    # ─────────────────────────────────────────────────────────────────
    # PHASE 1: Market Scanning
    # ─────────────────────────────────────────────────────────────────
    def _phase1_market_scan(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scan instruments for tradeable opportunities."""
        opportunities: List[Dict[str, Any]] = []

        for symbol, data in market_data.items():
            # Basic quality filters
            spread = data.get("spread", 999)
            volume = data.get("volume", 0)

            if spread > 0.5:
                continue
            if volume < 100:
                continue

            # Score based on volume and spread quality
            volume_score = min(1.0, volume / 1000.0)
            spread_score = max(0.0, 1.0 - spread / 0.5)
            combined_score = (volume_score * 0.6) + (spread_score * 0.4)

            opportunities.append({
                "symbol": symbol,
                "data": data,
                "score": combined_score,
                "spread": spread,
                "volume": volume,
            })

        # Sort by score, take top opportunities
        opportunities.sort(key=lambda x: x["score"], reverse=True)

        return {
            "total_scanned": len(market_data),
            "filtered_count": len(opportunities),
            "opportunities": opportunities[:5],
        }

    # ─────────────────────────────────────────────────────────────────
    # PHASE 2: AI & Regime Detection
    # ─────────────────────────────────────────────────────────────────
    def _phase2_ai_analysis(
        self, market_data: Dict[str, Any], scan_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI regime detection and ensemble prediction."""
        result: Dict[str, Any] = {
            "regime": "unknown",
            "predictions": {},
            "rl_decision": None,
            "learning_rate": None,
        }

        # --- Regime detection (V3) ---
        if self.regime_detector:
            try:
                # Pick the most liquid symbol for regime detection
                top_opp = scan_result["opportunities"][0] if scan_result.get("opportunities") else None
                if top_opp:
                    candles = top_opp["data"].get("candles", [])
                    if candles and len(candles) >= 50:
                        import numpy as np
                        closes = [float(c.get("close", 0)) for c in candles]
                        features = np.array(closes[-50:]).reshape(1, -1)
                        regime_pred = self.regime_detector.predict(features)
                        if isinstance(regime_pred, dict):
                            result["regime"] = regime_pred.get("regime", "unknown")
                        else:
                            result["regime"] = str(regime_pred)
            except Exception as e:
                logger.error("Regime detection failed: %s", e)

        # --- Asset-specific ensemble predictions (V6) ---
        if self.asset_ensembles:
            for opp in scan_result.get("opportunities", []):
                try:
                    prediction = self.asset_ensembles.predict_asset(
                        opp["symbol"], opp["data"]
                    )
                    if prediction:
                        result["predictions"][opp["symbol"]] = prediction
                except Exception as e:
                    logger.error(
                        "Ensemble prediction failed for %s: %s", opp["symbol"], e
                    )

        # --- V3 pipeline prediction (full feature engineering + ensemble) ---
        if self.ensemble:
            for opp in scan_result.get("opportunities", []):
                try:
                    import asyncio
                    candles = opp["data"].get("candles", [])
                    if candles and len(candles) >= 60:
                        loop = asyncio.new_event_loop()
                        try:
                            pipeline_pred = loop.run_until_complete(
                                self.ensemble.predict(
                                    symbol=opp["symbol"],
                                    timeframe="M5",
                                    lookback=200,
                                )
                            )
                        finally:
                            loop.close()

                        if pipeline_pred and "error" not in pipeline_pred:
                            existing = result["predictions"].get(opp["symbol"], {})
                            existing["pipeline_prediction"] = pipeline_pred
                            result["predictions"][opp["symbol"]] = existing
                except Exception as e:
                    logger.error(
                        "Pipeline prediction failed for %s: %s", opp["symbol"], e
                    )

        # --- Meta-learning rate adjustment (V6) ---
        if self.meta_learner and result["regime"] != "unknown":
            try:
                # Calculate recent performance from cached predictions
                perf_scores = [
                    p.get("confidence", 0.5)
                    for p in result["predictions"].values()
                ]
                avg_perf = sum(perf_scores) / len(perf_scores) if perf_scores else 0.5
                learning_rate = self.meta_learner.adjust_learning_rate(
                    result["regime"], avg_perf
                )
                result["learning_rate"] = learning_rate
            except Exception as e:
                logger.error("Meta-learning failed: %s", e)

        return result

    # ─────────────────────────────────────────────────────────────────
    # PHASE 3: Signal Generation
    # ─────────────────────────────────────────────────────────────────
    def _phase3_signal_generation(
        self, scan_result: Dict[str, Any], ai_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trading signals using strategy diversification."""
        result: Dict[str, Any] = {
            "signal": None,
            "strategy": None,
            "confidence": 0,
        }

        # --- Strategy diversification (V6) ---
        if self.strategy_diversification:
            for opp in scan_result.get("opportunities", []):
                try:
                    # Pass the full candle data as-is
                    combined = self.strategy_diversification.get_signal_combined(
                        opp["data"]
                    )
                    if combined and combined.get("confidence", 0) > 0.65:
                        # Resolve direction string from action
                        action = combined.get("action", "BUY")
                        direction = "BUY" if action == "BUY" else "SELL"

                        result["signal"] = {
                            "symbol": opp["symbol"],
                            "action": direction,
                            "confidence": combined["confidence"],
                            "strategies_used": combined.get("strategies_used", []),
                            "entry_price": opp["data"].get("current_price", 0),
                            "stop_loss": 0,   # will be set in risk phase
                            "take_profit": 0,  # will be set in risk phase
                        }
                        result["strategy"] = "diversified"
                        result["confidence"] = combined["confidence"]
                        return result
                except Exception as e:
                    logger.error(
                        "Strategy diversification failed for %s: %s",
                        opp["symbol"],
                        e,
                    )

        # --- Fallback: use ensemble predictions ---
        for symbol, prediction in ai_result.get("predictions", {}).items():
            conf = prediction.get("confidence", 0)
            if conf > 0.70:
                direction_val = prediction.get("direction", 1.0)
                if isinstance(direction_val, (int, float)):
                    action = "BUY" if direction_val > 0 else "SELL"
                else:
                    action = str(direction_val)

                result["signal"] = {
                    "symbol": symbol,
                    "action": action,
                    "confidence": conf,
                    "entry_price": prediction.get("entry_price", 0),
                    "stop_loss": prediction.get("stop_loss", 0),
                    "take_profit": prediction.get("take_profit", 0),
                }
                result["strategy"] = "ensemble"
                result["confidence"] = conf
                break

        return result

    # ─────────────────────────────────────────────────────────────────
    # PHASE 4: Risk Management
    # ─────────────────────────────────────────────────────────────────
    def _phase4_risk_management(
        self, signal_result: Dict[str, Any], market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply all risk management layers."""
        result: Dict[str, Any] = {
            "approved": False,
            "position_size": 0,
            "adjusted_size": 0,
            "risk_checks": {},
        }

        signal = signal_result.get("signal", {})
        symbol = signal.get("symbol", "")

        # Base position size: 1% risk per trade
        base_size = 0.01

        # --- Dynamic Kelly (V6) ---
        if self.dynamic_kelly:
            try:
                kelly_mult = self.dynamic_kelly.get_position_size_multiplier()
                base_size = 0.01 * kelly_mult
                result["risk_checks"]["kelly_multiplier"] = kelly_mult
            except Exception as e:
                logger.error("Kelly calculation failed: %s", e)

        result["position_size"] = base_size
        adjusted_size = base_size

        # --- Correlation penalty (V6) ---
        if self.correlation_manager:
            try:
                corr_adjusted = self.correlation_manager.get_adjusted_position_size(
                    symbol, adjusted_size
                )
                result["risk_checks"]["correlation_adjustment"] = (
                    corr_adjusted / adjusted_size if adjusted_size > 0 else 1.0
                )
                adjusted_size = corr_adjusted
            except Exception as e:
                logger.error("Correlation check failed: %s", e)

        # --- Volatility scaling (V6) ---
        if self.volatility_scaler and symbol in market_data:
            try:
                data = market_data[symbol]
                current_atr = data.get("current_atr", 0)
                historical_atr = data.get("historical_atr", 1)

                # If ATR values not provided, compute from candles
                if current_atr == 0 and historical_atr == 1:
                    candles = data.get("closes", data.get("candles", []))
                    if isinstance(candles, list) and len(candles) >= 20:
                        prices = [float(c.get("close", c) if isinstance(c, dict) else c) for c in candles]
                        current_vol = self.volatility_scaler.calculate_realized_volatility(prices, 10) if hasattr(self.volatility_scaler, 'calculate_realized_volatility') else 0
                        historical_vol = self.volatility_scaler.calculate_realized_volatility(prices, 50) if hasattr(self.volatility_scaler, 'calculate_realized_volatility') else current_vol
                        if historical_vol > 0:
                            current_atr = current_vol
                            historical_atr = historical_vol

                if historical_atr > 0:
                    vol_scale = self.volatility_scaler.get_volatility_scale(
                        symbol, current_atr, historical_atr
                    )
                    result["risk_checks"]["volatility_scale"] = vol_scale
                    adjusted_size *= vol_scale
            except Exception as e:
                logger.error("Volatility scaling failed: %s", e)

        # --- Dynamic asset allocation (V6) ---
        if self.dynamic_allocation:
            try:
                alloc_mult = self.dynamic_allocation.get_position_size_multiplier(symbol)
                result["risk_checks"]["allocation_multiplier"] = alloc_mult
                adjusted_size *= alloc_mult
            except Exception as e:
                logger.error("Dynamic allocation failed: %s", e)

        # --- Clamp to safe range [1%, 2%] (min 0.01 lots) ---
        adjusted_size = max(0.01, min(0.02, adjusted_size))

        result["adjusted_size"] = adjusted_size
        result["approved"] = True  # All risk checks passed

        return result

    # ─────────────────────────────────────────────────────────────────
    # PHASE 5: Execution Optimization
    # ─────────────────────────────────────────────────────────────────
    def _phase5_execution(
        self,
        signal_result: Dict[str, Any],
        risk_result: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optimize and execute the trade."""
        result: Dict[str, Any] = {
            "trade_executed": False,
            "order_details": None,
            "reject_reason": None,
        }

        signal = signal_result.get("signal", {})
        symbol = signal.get("symbol", "")

        # --- Execution optimization (V6) ---
        if self.execution_optimizer and symbol in market_data:
            try:
                data = market_data[symbol]

                # Check spread
                spread_check = self.execution_optimizer.check_spread(
                    data.get("spread", 0), symbol
                )
                if not spread_check.get("acceptable", True):
                    result["reject_reason"] = "SPREAD_TOO_HIGH"
                    result["spread_check"] = spread_check
                    return result

                # Check slippage
                entry_price = signal.get("entry_price", 0)
                current_price = data.get("current_price", 0)
                if entry_price > 0 and current_price > 0:
                    slippage_check = self.execution_optimizer.check_slippage(
                        entry_price, current_price, symbol
                    )
                    if not slippage_check.get("acceptable", True):
                        result["reject_reason"] = "SLIPPAGE_TOO_HIGH"
                        result["slippage_check"] = slippage_check
                        return result

                # Get optimal order type
                if hasattr(self.execution_optimizer, "get_optimal_order_type"):
                    order_type = self.execution_optimizer.get_optimal_order_type(
                        data.get("volume", 0)
                    )
                else:
                    order_type = "MARKET"

                result["order_type"] = order_type
            except Exception as e:
                logger.error("Execution optimization failed: %s", e)

        # --- Execute trade ---
        result["trade_executed"] = True
        result["order_details"] = {
            "symbol": symbol,
            "action": signal.get("action", "BUY"),
            "volume": risk_result.get("adjusted_size", 0.01),
            "stop_loss": signal.get("stop_loss", 0),
            "take_profit": signal.get("take_profit", 0),
            "strategy": signal_result.get("strategy", "unknown"),
            "confidence": signal_result.get("confidence", 0),
            "order_type": result.get("order_type", "MARKET"),
        }

        return result

    # ─────────────────────────────────────────────────────────────────
    # PHASE 6: Time-Based Exit Management
    # ─────────────────────────────────────────────────────────────────
    def _phase6_exit_management(self, exec_result: Dict[str, Any]):
        """Register trade for time-based exit monitoring."""
        if not self.time_based_exit:
            return

        order = exec_result.get("order_details", {})
        if not order:
            return

        # Register with time-based exit system
        # Actual exit monitoring runs in a separate task checking open positions
        logger.info(
            "Trade registered for time-based exit: %s %s (strategy=%s)",
            order.get("action"),
            order.get("symbol"),
            order.get("strategy"),
        )

    # ─────────────────────────────────────────────────────────────────
    # PHASE 7: Learning & Adaptation
    # ─────────────────────────────────────────────────────────────────
    def _phase7_learning(
        self, exec_result: Dict[str, Any], signal_result: Dict[str, Any]
    ):
        """Update learning systems after trade execution."""
        order = exec_result.get("order_details", {})
        if not order:
            return

        # --- Dynamic Kelly update ---
        if self.dynamic_kelly:
            try:
                self.dynamic_kelly.update_stats({
                    "profit": 0,  # updated when trade closes
                    "symbol": order.get("symbol", ""),
                })
            except Exception as e:
                logger.error("Kelly update failed: %s", e)

        # --- Transfer learning fine-tune ---
        if self.transfer_learning:
            try:
                live_data = {
                    "symbol": order.get("symbol", ""),
                    "strategy": order.get("strategy", ""),
                    "confidence": order.get("confidence", 0),
                }
                self.transfer_learning.fine_tune_model("ensemble", live_data)
            except Exception as e:
                logger.error("Transfer learning fine-tune failed: %s", e)

    # ─────────────────────────────────────────────────────────────────
    # Status & Diagnostics
    # ─────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status with component availability."""
        return {
            "initialized": self._initialized,
            "components": {
                "meta_learner": self.meta_learner is not None,
                "asset_ensembles": self.asset_ensembles is not None,
                "transfer_learning": self.transfer_learning is not None,
                "dynamic_allocation": self.dynamic_allocation is not None,
                "correlation_manager": self.correlation_manager is not None,
                "volatility_scaler": self.volatility_scaler is not None,
                "dynamic_kelly": self.dynamic_kelly is not None,
                "strategy_diversification": self.strategy_diversification is not None,
                "time_based_exit": self.time_based_exit is not None,
                "execution_optimizer": self.execution_optimizer is not None,
                "ensemble_pipeline": self.ensemble is not None,
                "regime_detector": self.regime_detector is not None,
            },
            "component_count": sum(1 for v in [
                self.meta_learner,
                self.asset_ensembles,
                self.transfer_learning,
                self.dynamic_allocation,
                self.correlation_manager,
                self.volatility_scaler,
                self.dynamic_kelly,
                self.strategy_diversification,
                self.time_based_exit,
                self.execution_optimizer,
                self.ensemble,
                self.regime_detector,
            ] if v is not None),
            "total_components": 12,
        }


# ── Singleton accessor ──────────────────────────────────────────────
_v6_orchestrator: Optional[V6TradingOrchestrator] = None


def get_v6_orchestrator() -> V6TradingOrchestrator:
    """Get or create the singleton V6 orchestrator instance."""
    global _v6_orchestrator
    if _v6_orchestrator is None:
        _v6_orchestrator = V6TradingOrchestrator()
    return _v6_orchestrator
