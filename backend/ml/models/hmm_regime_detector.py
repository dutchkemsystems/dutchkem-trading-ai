"""
HMM Regime Detector — Hidden Markov Model based market regime classification.

Uses hmmlearn GaussianHMM when available; falls back to a simple
volatility-based heuristic otherwise.

5 regimes:
    TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, BREAKOUT
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.models.hmm_regime_detector")

# Try to import hmmlearn
try:
    from hmmlearn.hmm import GaussianHMM
    _HMM_AVAILABLE = True
except ImportError:
    GaussianHMM = None  # type: ignore[assignment,misc]
    _HMM_AVAILABLE = False
    logger.info("hmmlearn not installed — using volatility-heuristic fallback")

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    np = None  # type: ignore[assignment]
    _NP_AVAILABLE = False


class HMMRegimeDetector:
    """
    Hidden Markov Model regime detector with 5 market regimes.

    When hmmlearn is available the model is trained via ``fit()`` and
    predictions use the Viterbi path.  Otherwise a simple volatility-
    and trend-based heuristic is used as a fallback.
    """

    REGIMES = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE", "BREAKOUT"]

    def __init__(self, n_regimes: int = 5, n_iter: int = 100, random_state: int = 42):
        self.n_regimes = n_regimes
        self.n_iter = n_iter
        self.random_state = random_state
        self._model: Optional[Any] = None
        self._fitted = False
        self._regime_order: List[str] = []

    # ── Training ────────────────────────────────────────────────────

    def fit(self, returns: Any) -> Dict[str, Any]:
        """
        Train the HMM on historical log-returns.

        Parameters
        ----------
        returns : array-like
            1-D or 2-D array of returns.  If 2-D, each column is a feature.

        Returns
        -------
        dict with training summary or error info.
        """
        if not _HMM_AVAILABLE or not _NP_AVAILABLE:
            return {"error": "hmmlearn/numpy not available", "method": "heuristic"}

        returns = np.asarray(returns, dtype=np.float64)
        if returns.ndim == 1:
            returns = returns.reshape(-1, 1)

        if len(returns) < 50:
            return {"error": "Insufficient data (need >=50 observations)"}

        # Remove NaN / Inf
        mask = np.isfinite(returns).all(axis=1)
        returns = returns[mask]
        if len(returns) < 50:
            return {"error": "Insufficient finite data after cleaning"}

        try:
            self._model = GaussianHMM(
                n_components=self.n_regimes,
                covariance_type="diag",
                n_iter=self.n_iter,
                random_state=self.random_state,
            )
            self._model.fit(returns)
            self._fitted = True

            # Map hidden states to named regimes based on mean returns
            means = self._model.means_.flatten()
            sorted_indices = np.argsort(means)
            regime_map = {}
            labels = ["TRENDING_DOWN", "RANGING_LOW", "RANGING", "RANGING_HIGH", "TRENDING_UP"]
            for rank, idx in enumerate(sorted_indices):
                regime_map[int(idx)] = labels[min(rank, len(labels) - 1)]

            # Merge RANGING_LOW / RANGING_HIGH into RANGING
            for k in regime_map:
                if regime_map[k] in ("RANGING_LOW", "RANGING_HIGH"):
                    regime_map[k] = "RANGING"

            self._regime_order = [regime_map.get(i, "RANGING") for i in range(self.n_regimes)]

            logger.info("HMM fitted on %d observations — means: %s", len(returns), means.tolist())
            return {
                "status": "fitted",
                "observations": len(returns),
                "means": means.tolist(),
                "regime_mapping": self._regime_order,
            }
        except Exception as e:
            logger.error("HMM fit failed: %s", e)
            self._fitted = False
            return {"error": str(e)}

    # ── Prediction ──────────────────────────────────────────────────

    def predict(self, returns: Any) -> str:
        """
        Predict the current regime.

        Returns a regime string or "UNKNOWN" if the model is not fitted.
        """
        if not self._fitted or self._model is None:
            return self._heuristic_predict(returns)

        if not _NP_AVAILABLE:
            return "UNKNOWN"

        try:
            returns = np.asarray(returns, dtype=np.float64)
            if returns.ndim == 1:
                returns = returns.reshape(-1, 1)

            states = self._model.predict(returns)
            last_state = int(states[-1])

            if last_state < len(self._regime_order):
                return self._regime_order[last_state]
            return "UNKNOWN"
        except Exception as e:
            logger.error("HMM predict failed: %s", e)
            return "UNKNOWN"

    def predict_proba(self, returns: Any) -> Dict[str, float]:
        """
        Return probability dict for each regime.

        Falls back to heuristic if model is not fitted.
        """
        if not self._fitted or self._model is None:
            return self._heuristic_predict_proba(returns)

        if not _NP_AVAILABLE:
            return {r: 0.0 for r in self.REGIMES}

        try:
            returns = np.asarray(returns, dtype=np.float64)
            if returns.ndim == 1:
                returns = returns.reshape(-1, 1)

            probs = self._model.predict_proba(returns)
            last_probs = probs[-1]

            result: Dict[str, float] = {}
            for regime_name in self.REGIMES:
                result[regime_name] = 0.0

            for state_idx, prob in enumerate(last_probs):
                if state_idx < len(self._regime_order):
                    mapped = self._regime_order[state_idx]
                    if mapped in result:
                        result[mapped] += float(prob)
                    else:
                        result[mapped] = float(prob)

            return result
        except Exception as e:
            logger.error("HMM predict_proba failed: %s", e)
            return {r: 0.0 for r in self.REGIMES}

    # ── Heuristic fallback ──────────────────────────────────────────

    def _to_list(self, returns: Any) -> List[float]:
        """Convert returns to a plain float list."""
        if _NP_AVAILABLE and hasattr(returns, "tolist"):
            arr = np.asarray(returns, dtype=np.float64).flatten()
            return arr.tolist()
        if isinstance(returns, (list, tuple)):
            return [float(x) for x in returns]
        return []

    def _heuristic_predict(self, returns: Any) -> str:
        """Simple volatility-based regime classification."""
        vals = self._to_list(returns)
        if len(vals) < 10:
            return "UNKNOWN"

        # Volatility (std dev of recent returns)
        recent = vals[-20:] if len(vals) >= 20 else vals
        mean_r = sum(recent) / len(recent)
        variance = sum((r - mean_r) ** 2 for r in recent) / len(recent)
        vol = variance ** 0.5

        # Trend (recent cumulative return)
        lookback = min(50, len(vals))
        cumulative = sum(vals[-lookback:])

        # Classify
        vol_threshold_high = 0.02
        vol_threshold_low = 0.005
        trend_threshold = 0.01

        if vol > vol_threshold_high:
            if abs(cumulative) > trend_threshold * 2:
                return "BREAKOUT"
            return "VOLATILE"
        elif cumulative > trend_threshold:
            return "TRENDING_UP"
        elif cumulative < -trend_threshold:
            return "TRENDING_DOWN"
        else:
            return "RANGING"

    def _heuristic_predict_proba(self, returns: Any) -> Dict[str, float]:
        """Probabilities from heuristic."""
        regime = self._heuristic_predict(returns)
        probs = {r: 0.0 for r in self.REGIMES}
        if regime in probs:
            probs[regime] = 1.0
        else:
            probs["RANGING"] = 1.0
        return probs
