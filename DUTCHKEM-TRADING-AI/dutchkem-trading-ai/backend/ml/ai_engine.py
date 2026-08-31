"""
V6 AI Engine — Unified facade for all ML components.

Lazy-loads RegimeDetector, PredictionPipeline, RLAgent, MetaLearner,
TransferLearning, and AssetEnsemble. Provides a single predict() entry
point that combines all model outputs with graceful fallback.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.ai_engine")


class AIEngine:
    """
    Central AI engine that orchestrates all ML sub-components.

    Components are lazy-loaded on first use. If any component fails to
    import or initialise, it is marked unhealthy and skipped in future
    predictions — one failure never blocks the others.
    """

    def __init__(self):
        self.regime_detector = None
        self.prediction_pipeline = None
        self.rl_agent = None
        self.meta_learner = None
        self.transfer_learning = None
        self.asset_ensemble = None

        self._component_health: Dict[str, bool] = {}
        self._initialized = False

    # ── Lazy loader ─────────────────────────────────────────────────

    def _lazy_load(self, module_path: str, attr_name: str, friendly_name: str):
        """Import *attr_name* from *module_path*, instantiate, and cache."""
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, attr_name)
            instance = cls()
            logger.info("AIEngine loaded: %s", friendly_name)
            self._component_health[friendly_name] = True
            return instance
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("AIEngine optional component not installed: %s (%s)", friendly_name, e)
            self._component_health[friendly_name] = False
            return None
        except AttributeError as e:
            logger.error("AIEngine component class missing: %s (%s)", friendly_name, e)
            self._component_health[friendly_name] = False
            return None
        except Exception as e:
            logger.error("AIEngine component failed to initialise: %s (%s)", friendly_name, e, exc_info=True)
            self._component_health[friendly_name] = False
            return None

    # ── Initialisation ──────────────────────────────────────────────

    def initialize(self):
        """Lazy-load every sub-component. Safe to call multiple times."""
        if self._initialized:
            return

        self.regime_detector = self._lazy_load(
            "ml.models.regime_detector", "RegimeDetector", "RegimeDetector",
        )
        self.prediction_pipeline = self._lazy_load(
            "ml.pipeline", "PredictionPipeline", "PredictionPipeline",
        )
        self.rl_agent = self._lazy_load(
            "ml.models.rl_agent", "RLAgent", "RLAgent",
        )
        self.meta_learner = self._lazy_load(
            "ml.meta_learner", "MetaLearner", "MetaLearner",
        )
        self.transfer_learning = self._lazy_load(
            "ml.transfer_learning", "TransferLearning", "TransferLearning",
        )
        self.asset_ensemble = self._lazy_load(
            "ml.asset_ensemble", "AssetClassEnsemble", "AssetEnsemble",
        )

        self._initialized = True
        loaded = sum(1 for v in self._component_health.values() if v)
        logger.info("AIEngine initialised — %d/6 components loaded", loaded)

    @property
    def component_count(self) -> int:
        components = [
            self.regime_detector, self.prediction_pipeline, self.rl_agent,
            self.meta_learner, self.transfer_learning, self.asset_ensemble,
        ]
        return sum(1 for c in components if c is not None)

    # ── Public API ──────────────────────────────────────────────────

    def predict(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combined prediction from all available models.

        Returns dict with keys: regime, direction, confidence, ensemble,
        components_used, component_health.
        """
        self.initialize()
        result: Dict[str, Any] = {
            "symbol": symbol,
            "regime": "unknown",
            "direction": 0.0,
            "confidence": 0.0,
            "ensemble": {},
            "components_used": 0,
        }

        scores: List[float] = []
        weights: List[float] = []

        # 1. Regime detection
        regime_info = self.get_regime(market_data)
        if regime_info.get("regime") and regime_info["regime"] != "unknown":
            result["regime"] = regime_info["regime"]
            result["components_used"] += 1

        # 2. Ensemble prediction
        ensemble_pred = self.get_ensemble_prediction(symbol, market_data)
        if ensemble_pred.get("direction"):
            result["direction"] = ensemble_pred["direction"]
            result["confidence"] = ensemble_pred.get("confidence", 0.0)
            result["ensemble"] = ensemble_pred
            result["components_used"] += 1

            scores.append(ensemble_pred["direction"] * ensemble_pred.get("confidence", 0.5))
            weights.append(1.0)

        # 3. Asset ensemble
        if self.asset_ensemble:
            try:
                asset_pred = self.asset_ensemble.predict(symbol, market_data)
                if asset_pred and "direction" in asset_pred:
                    d = asset_pred["direction"]
                    c = asset_pred.get("confidence", 0.5)
                    scores.append(d * c)
                    weights.append(0.8)
                    result["components_used"] += 1
            except Exception as e:
                logger.error("AssetEnsemble prediction failed: %s", e)

        # 4. RL agent
        if self.rl_agent:
            try:
                rl_action = self.rl_agent.predict(market_data)
                if rl_action and "action" in rl_action:
                    rl_dir = 1.0 if rl_action["action"] == "BUY" else -1.0
                    rl_conf = rl_action.get("confidence", 0.5)
                    scores.append(rl_dir * rl_conf)
                    weights.append(0.6)
                    result["components_used"] += 1
            except Exception as e:
                logger.error("RLAgent prediction failed: %s", e)

        # 5. Weighted average
        if scores and weights:
            total_weight = sum(weights)
            if total_weight > 0:
                weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
                result["direction"] = weighted_score
                result["confidence"] = min(1.0, abs(weighted_score))

        return result

    def get_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect current market regime using RegimeDetector."""
        self.initialize()
        if not self.regime_detector:
            return {"regime": "unknown", "confidence": 0.0}

        try:
            import numpy as np
            closes = []
            # Try to extract closes from market_data
            for sym_data in market_data.values():
                if isinstance(sym_data, dict):
                    candle_closes = sym_data.get("closes", [])
                    if not candle_closes:
                        candles = sym_data.get("candles", [])
                        candle_closes = [float(c.get("close", 0)) for c in candles] if candles else []
                    if candle_closes and len(candle_closes) >= 50:
                        closes = candle_closes[-50:]
                        break

            if not closes or len(closes) < 50:
                return {"regime": "unknown", "confidence": 0.0}

            features = np.array(closes).reshape(1, -1)
            pred = self.regime_detector.predict(features)
            if isinstance(pred, dict):
                return {"regime": pred.get("regime", "unknown"), "confidence": pred.get("confidence", 0.0)}
            return {"regime": str(pred), "confidence": 0.5}
        except Exception as e:
            logger.error("Regime detection failed: %s", e)
            return {"regime": "unknown", "confidence": 0.0}

    def get_ensemble_prediction(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get prediction from the PredictionPipeline."""
        self.initialize()
        if not self.prediction_pipeline:
            return {"direction": 0.0, "confidence": 0.0}

        try:
            import asyncio

            async def _predict():
                return await self.prediction_pipeline.predict(
                    symbol=symbol, timeframe="M5", lookback=200,
                )

            pred = asyncio.run(_predict())
            if pred and "error" not in pred:
                direction = pred.get("direction", 0.0)
                if isinstance(direction, (int, float)):
                    return {
                        "direction": float(direction),
                        "confidence": float(pred.get("confidence", 0.0)),
                        "entry_price": pred.get("entry_price", 0.0),
                        "stop_loss": pred.get("stop_loss", 0.0),
                        "take_profit": pred.get("take_profit", 0.0),
                    }
            return {"direction": 0.0, "confidence": 0.0}
        except Exception as e:
            logger.error("Ensemble prediction failed for %s: %s", symbol, e)
            return {"direction": 0.0, "confidence": 0.0}

    def update_from_trade(self, trade_result: Dict[str, Any]) -> None:
        """
        Feed a completed trade result back to all models that support
        online / incremental learning.
        """
        self.initialize()

        # MetaLearner
        if self.meta_learner:
            try:
                regime = trade_result.get("regime", "unknown")
                profit = trade_result.get("profit", 0)
                self.meta_learner.adjust_learning_rate(regime, 1.0 if profit > 0 else 0.0)
                logger.info("MetaLearner updated from trade (regime=%s, profit=%.2f)", regime, profit)
            except Exception as e:
                logger.error("MetaLearner update failed: %s", e)

        # TransferLearning
        if self.transfer_learning:
            try:
                self.transfer_learning.fine_tune_model("ensemble", trade_result)
                logger.info("TransferLearning fine-tuned from trade")
            except Exception as e:
                logger.error("TransferLearning update failed: %s", e)

        # RL Agent
        if self.rl_agent:
            try:
                reward = trade_result.get("profit", 0)
                self.rl_agent.update(reward, trade_result)
                logger.info("RLAgent updated with reward=%.2f", reward)
            except Exception as e:
                logger.error("RLAgent update failed: %s", e)

    def get_health(self) -> Dict[str, bool]:
        """Return component health map."""
        self.initialize()
        return self._component_health.copy()
