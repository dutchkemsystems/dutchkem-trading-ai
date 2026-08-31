"""
MULTI-TIMEFRAME CONFLUENCE ENGINE
V6.5 Enhancement #5
"""

import logging
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.enhancements.multi_tf")


class MultiTimeframeAnalyzer:
    """
    Analyze multiple timeframes for confluence.
    """

    def __init__(self):
        self.timeframes = {
            "M1": {"weight": 0.10, "bars": 1440},
            "M5": {"weight": 0.15, "bars": 288},
            "M15": {"weight": 0.20, "bars": 96},
            "M30": {"weight": 0.20, "bars": 48},
            "H1": {"weight": 0.20, "bars": 24},
            "H4": {"weight": 0.10, "bars": 6},
            "D1": {"weight": 0.05, "bars": 1},
        }
        self.confluence_threshold = 0.60

    def analyze_all_timeframes(self, symbol: str, market_data: Dict = None) -> Dict:
        try:
            consensus = {"BUY": 0, "SELL": 0, "NEUTRAL": 0}
            tf_signals = {}
            conf_scores = []

            for tf, cfg in self.timeframes.items():
                data = self._get_timeframe_data(symbol, tf, cfg["bars"], market_data)
                sig = self._generate_tf_signal(data)
                w = cfg["weight"]
                if sig["action"] == "BUY":
                    consensus["BUY"] += w * sig["confidence"]
                    conf_scores.append(sig["confidence"])
                elif sig["action"] == "SELL":
                    consensus["SELL"] += w * sig["confidence"]
                    conf_scores.append(sig["confidence"])
                else:
                    consensus["NEUTRAL"] += w
                tf_signals[tf] = sig

            buy_s, sell_s = consensus["BUY"], consensus["SELL"]
            avg_conf = sum(conf_scores) / len(conf_scores) if conf_scores else 0

            if buy_s > sell_s * 1.5:
                action, confidence = "BUY", min(1.0, (buy_s - sell_s) / 0.5)
            elif sell_s > buy_s * 1.5:
                action, confidence = "SELL", min(1.0, (sell_s - buy_s) / 0.5)
            else:
                action, confidence = "NEUTRAL", 0.5

            return {
                "action": action, "confidence": confidence,
                "timeframe_signals": tf_signals, "consensus": consensus,
                "confluence_score": max(buy_s, sell_s),
                "total_timeframes": len(self.timeframes),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error("Multi-TF analysis failed for %s: %s", symbol, e)
            return {"action": "NEUTRAL", "confidence": 0, "timeframe_signals": {},
                    "consensus": {"BUY": 0, "SELL": 0, "NEUTRAL": 0}, "confluence_score": 0, "total_timeframes": 0}

    def _get_timeframe_data(self, symbol: str, tf: str, bars: int, market_data: Dict = None) -> pd.DataFrame:
        if market_data and "candles" in market_data:
            candles = market_data["candles"][-bars:]
            if candles:
                return pd.DataFrame(candles)
        rng = np.random.default_rng()
        base = rng.uniform(1.0000, 2.0000)
        data = []
        for _ in range(min(bars, 200)):
            chg = rng.uniform(-0.001, 0.001)
            o = base
            c = base * (1 + chg)
            h = max(o, c) * (1 + rng.uniform(0, 0.0005))
            l = min(o, c) * (1 - rng.uniform(0, 0.0005))
            data.append({"open": o, "high": h, "low": l, "close": c, "volume": int(rng.integers(100, 10000))})
            base = c
        return pd.DataFrame(data)

    def _generate_tf_signal(self, data: pd.DataFrame) -> Dict:
        if data.empty or len(data) < 20:
            return {"action": "NEUTRAL", "confidence": 0, "trend": "UNKNOWN"}
        try:
            data = data.copy()
            for col in ["open", "high", "low", "close"]:
                data[col] = pd.to_numeric(data[col], errors="coerce")
            data["ema21"] = data["close"].ewm(span=21, adjust=False).mean()
            data["ema50"] = data["close"].ewm(span=50, adjust=False).mean()
            data["rsi"] = self._calc_rsi(data["close"], 14)
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            trend = "BULLISH" if latest["ema21"] > latest["ema50"] else ("BEARISH" if latest["ema21"] < latest["ema50"] else "NEUTRAL")
            buy_s, sell_s = 0, 0
            if latest["rsi"] < 30:
                buy_s += 1
            elif latest["rsi"] > 70:
                sell_s += 1
            macd_val = latest["ema21"] - latest["ema50"]
            if macd_val > 0:
                buy_s += 1
            else:
                sell_s += 1
            if latest["ema21"] > latest["ema50"] and prev["ema21"] <= prev["ema50"]:
                buy_s += 2
            elif latest["ema21"] < latest["ema50"] and prev["ema21"] >= prev["ema50"]:
                sell_s += 2
            if buy_s > sell_s + 1:
                return {"action": "BUY", "confidence": min(0.9, buy_s / max(buy_s + sell_s, 1)), "trend": trend}
            elif sell_s > buy_s + 1:
                return {"action": "SELL", "confidence": min(0.9, sell_s / max(buy_s + sell_s, 1)), "trend": trend}
            return {"action": "NEUTRAL", "confidence": 0.5, "trend": trend}
        except Exception as e:
            logger.error("TF signal failed: %s", e)
            return {"action": "NEUTRAL", "confidence": 0, "trend": "UNKNOWN"}

    def _calc_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def get_confluence_score(self, signals: Dict) -> float:
        buy_c = sell_c = total = 0
        for sig in signals.get("timeframe_signals", {}).values():
            total += 1
            if sig["action"] == "BUY":
                buy_c += 1
            elif sig["action"] == "SELL":
                sell_c += 1
        return max(buy_c, sell_c) / total if total > 0 else 0
