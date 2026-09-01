"""
DEEP LEARNING PATTERN RECOGNITION ENGINE
V6.5 Enhancement #4
"""

import logging
from datetime import datetime
from typing import Dict, List

import numpy as np

logger = logging.getLogger("ml.enhancements.pattern_recognizer")


class DeepPatternRecognizer:
    """
    CNN-based pattern recognition for candlestick patterns.
    Falls back to rule-based detection when TensorFlow is unavailable.
    """

    def __init__(self):
        self.model = None
        self.confidence_threshold = 0.7
        self.sequence_length = 100
        self.feature_count = 4
        self.model_loaded = False

    def build_model(self):
        try:
            import tensorflow as tf
            from tensorflow.keras import layers, models

            model = models.Sequential([
                layers.Conv1D(64, 3, activation="relu", input_shape=(self.sequence_length, self.feature_count)),
                layers.Conv1D(64, 3, activation="relu"),
                layers.MaxPooling1D(2),
                layers.Conv1D(128, 3, activation="relu"),
                layers.Conv1D(128, 3, activation="relu"),
                layers.MaxPooling1D(2),
                layers.Conv1D(256, 3, activation="relu"),
                layers.Conv1D(256, 3, activation="relu"),
                layers.GlobalAveragePooling1D(),
                layers.Dense(128, activation="relu"),
                layers.Dropout(0.3),
                layers.Dense(64, activation="relu"),
                layers.Dropout(0.2),
                layers.Dense(3, activation="softmax"),
            ])
            model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
            self.model = model
            self.model_loaded = True
            logger.info("CNN pattern model built")
        except ImportError:
            logger.warning("TensorFlow not available — using rule-based pattern detection")
            self.model_loaded = False

    def recognize_pattern(self, bars: np.ndarray) -> Dict:
        try:
            if bars is None or len(bars) < 3:
                return {"direction": 0, "confidence": 0, "pattern_type": [], "signal": "NEUTRAL"}

            if self.model_loaded and self.model is not None:
                return self._cnn_predict(bars)
            return self._rule_based_detect(bars)
        except Exception as e:
            logger.error("Pattern recognition failed: %s", e)
            return {"direction": 0, "confidence": 0, "pattern_type": [], "signal": "NEUTRAL"}

    def _cnn_predict(self, bars: np.ndarray) -> Dict:
        normalized = self._normalize_bars(bars)
        if normalized is None:
            return {"direction": 0, "confidence": 0, "pattern_type": [], "signal": "NEUTRAL"}
        prediction = self.model.predict(normalized, verbose=0)
        direction = int(np.argmax(prediction))
        confidence = float(np.max(prediction))
        patterns = self.identify_pattern_types(bars[-10:])
        return {
            "direction": direction, "confidence": confidence,
            "pattern_type": patterns,
            "signal": self._map_signal(direction, confidence),
            "timestamp": datetime.now().isoformat(),
        }

    def _rule_based_detect(self, bars: np.ndarray) -> Dict:
        recent = bars[-10:] if len(bars) > 10 else bars
        patterns = self.identify_pattern_types(recent)
        bullish = {"BULLISH_ENGULFING", "HAMMER", "MORNING_STAR", "PIERCING"}
        bearish = {"BEARISH_ENGULFING", "SHOOTING_STAR", "EVENING_STAR", "DARK_CLOUD_COVER"}

        if bullish.intersection(patterns):
            conf = min(0.85, 0.6 + len(bullish.intersection(patterns)) * 0.1)
            return {"direction": 0, "confidence": conf, "pattern_type": patterns, "signal": "BUY", "timestamp": datetime.now().isoformat()}
        elif bearish.intersection(patterns):
            conf = min(0.85, 0.6 + len(bearish.intersection(patterns)) * 0.1)
            return {"direction": 1, "confidence": conf, "pattern_type": patterns, "signal": "SELL", "timestamp": datetime.now().isoformat()}
        return {"direction": 2, "confidence": 0.3, "pattern_type": patterns, "signal": "NEUTRAL", "timestamp": datetime.now().isoformat()}

    def _normalize_bars(self, bars: np.ndarray) -> np.ndarray:
        try:
            if len(bars) < self.sequence_length:
                pad = self.sequence_length - len(bars)
                bars = np.pad(bars, ((pad, 0), (0, 0)), mode="constant")
            bars = bars[-self.sequence_length:]
            base = bars[0, 0] or 1.0
            normalized = bars / base
            return normalized.reshape(1, self.sequence_length, self.feature_count)
        except Exception:
            return None

    def identify_pattern_types(self, bars: np.ndarray) -> List[str]:
        patterns = []
        if len(bars) < 3:
            return patterns
        if self._is_doji(bars[-1]):
            patterns.append("DOJI")
        if len(bars) >= 2:
            if self._is_bullish_engulfing(bars[-2:]):
                patterns.append("BULLISH_ENGULFING")
            elif self._is_bearish_engulfing(bars[-2:]):
                patterns.append("BEARISH_ENGULFING")
        if self._is_hammer(bars[-1]):
            patterns.append("HAMMER")
        if self._is_shooting_star(bars[-1]):
            patterns.append("SHOOTING_STAR")
        if len(bars) >= 3:
            if self._is_morning_star(bars[-3:]):
                patterns.append("MORNING_STAR")
            elif self._is_evening_star(bars[-3:]):
                patterns.append("EVENING_STAR")
        if len(bars) >= 2:
            if self._is_piercing_pattern(bars[-2:]):
                patterns.append("PIERCING")
            if self._is_dark_cloud_cover(bars[-2:]):
                patterns.append("DARK_CLOUD_COVER")
        return patterns

    def _is_doji(self, bar) -> bool:
        o, h, l, c = float(bar[0]), float(bar[1]), float(bar[2]), float(bar[3])
        body = abs(c - o)
        rng = h - l
        return body / rng < 0.1 if rng > 0 else False

    def _is_bullish_engulfing(self, bars) -> bool:
        po, _, _, pc = float(bars[0][0]), float(bars[0][1]), float(bars[0][2]), float(bars[0][3])
        co, _, _, cc = float(bars[1][0]), float(bars[1][1]), float(bars[1][2]), float(bars[1][3])
        return pc < po and cc > co and co < pc and cc > po

    def _is_bearish_engulfing(self, bars) -> bool:
        po, _, _, pc = float(bars[0][0]), float(bars[0][1]), float(bars[0][2]), float(bars[0][3])
        co, _, _, cc = float(bars[1][0]), float(bars[1][1]), float(bars[1][2]), float(bars[1][3])
        return pc > po and cc < co and co > pc and cc < po

    def _is_hammer(self, bar) -> bool:
        o, h, l, c = float(bar[0]), float(bar[1]), float(bar[2]), float(bar[3])
        body = abs(c - o)
        lower = min(o, c) - l
        upper = h - max(o, c)
        return body > 0 and lower > 2 * body and upper < 0.1 * body

    def _is_shooting_star(self, bar) -> bool:
        o, h, l, c = float(bar[0]), float(bar[1]), float(bar[2]), float(bar[3])
        body = abs(c - o)
        upper = h - max(o, c)
        lower = min(o, c) - l
        return body > 0 and upper > 2 * body and lower < 0.1 * body

    def _is_morning_star(self, bars) -> bool:
        fo, _, _, fc = float(bars[0][0]), float(bars[0][1]), float(bars[0][2]), float(bars[0][3])
        so, sh, sl, sc = float(bars[1][0]), float(bars[1][1]), float(bars[1][2]), float(bars[1][3])
        to, _, _, tc = float(bars[2][0]), float(bars[2][1]), float(bars[2][2]), float(bars[2][3])
        s_body = abs(sc - so)
        s_range = sh - sl
        return (fc < fo and s_body / s_range < 0.3 if s_range > 0 else False) and tc > to and tc > (fo + fc) / 2

    def _is_evening_star(self, bars) -> bool:
        fo, _, _, fc = float(bars[0][0]), float(bars[0][1]), float(bars[0][2]), float(bars[0][3])
        so, sh, sl, sc = float(bars[1][0]), float(bars[1][1]), float(bars[1][2]), float(bars[1][3])
        to, _, _, tc = float(bars[2][0]), float(bars[2][1]), float(bars[2][2]), float(bars[2][3])
        s_body = abs(sc - so)
        s_range = sh - sl
        return (fc > fo and s_body / s_range < 0.3 if s_range > 0 else False) and tc < to and tc < (fo + fc) / 2

    def _is_piercing_pattern(self, bars) -> bool:
        po, _, _, pc = float(bars[0][0]), float(bars[0][1]), float(bars[0][2]), float(bars[0][3])
        co, _, _, cc = float(bars[1][0]), float(bars[1][1]), float(bars[1][2]), float(bars[1][3])
        return pc < po and cc > co and co < pc and cc > (po + pc) / 2

    def _is_dark_cloud_cover(self, bars) -> bool:
        po, _, _, pc = float(bars[0][0]), float(bars[0][1]), float(bars[0][2]), float(bars[0][3])
        co, _, _, cc = float(bars[1][0]), float(bars[1][1]), float(bars[1][2]), float(bars[1][3])
        return pc > po and cc < co and co > pc and cc < (po + pc) / 2

    def _map_signal(self, direction: int, confidence: float) -> str:
        if direction == 0 and confidence > self.confidence_threshold:
            return "BUY"
        elif direction == 1 and confidence > self.confidence_threshold:
            return "SELL"
        return "NEUTRAL"
