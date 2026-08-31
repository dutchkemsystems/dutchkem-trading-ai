"""
V2 Spike Detector — Price spike and flash crash detection and alerting.
"""
import logging
import time
from typing import Dict, Any, Optional, List
from collections import deque
from datetime import datetime
import numpy as np

logger = logging.getLogger('scalping.spike')


class SpikeType:
    SPIKE_UP = 'spike_up'
    SPIKE_DOWN = 'spike_down'
    FLASH_CRASH = 'flash_crash'
    FLASH_PUMP = 'flash_pump'


class SpikeEvent:
    def __init__(self, symbol: str, spike_type: str, magnitude: float, price: float):
        self.symbol = symbol
        self.spike_type = spike_type
        self.magnitude = magnitude
        self.price = price
        self.timestamp = datetime.now()
        self.confidence = min(1.0, magnitude / 3.0)
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'type': self.spike_type,
            'magnitude': round(self.magnitude, 2),
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'confidence': round(self.confidence, 2),
        }


class SpikeDetector:
    def __init__(self):
        self.spike_history: deque = deque(maxlen=1000)
        self.atr_multiplier = 3.0
        self.flash_crash_threshold = 5.0
        self.min_confirmation_bars = 2
        self.alert_callbacks: List = []
    
    def detect(self, symbol: str, data: Dict) -> Optional[SpikeEvent]:
        closes = np.array(data.get('close', []))
        highs = np.array(data.get('high', []))
        lows = np.array(data.get('low', []))
        
        if len(closes) < 20 or len(highs) < 20 or len(lows) < 20:
            return None
        
        # Calculate ATR
        tr = np.maximum(
            highs[-14:] - lows[-14:],
            np.maximum(
                np.abs(highs[-14:] - np.roll(closes, 1)[-14:]),
                np.abs(lows[-14:] - np.roll(closes, 1)[-14:])
            )
        )
        atr = float(np.mean(tr))
        
        if atr <= 0:
            return None
        
        # Check last price move
        current_price = closes[-1]
        prev_price = closes[-2]
        move = abs(current_price - prev_price)
        move_atr = move / atr
        
        if move_atr >= self.flash_crash_threshold:
            spike_type = SpikeType.FLASH_CRASH if current_price < prev_price else SpikeType.FLASH_PUMP
            event = SpikeEvent(symbol, spike_type, move_atr, current_price)
            self.spike_history.append(event)
            self._alert(event)
            return event
        
        if move_atr >= self.atr_multiplier:
            spike_type = SpikeType.SPIKE_UP if current_price > prev_price else SpikeType.SPIKE_DOWN
            event = SpikeEvent(symbol, spike_type, move_atr, current_price)
            self.spike_history.append(event)
            self._alert(event)
            return event
        
        return None
    
    def _alert(self, event: SpikeEvent):
        logger.warning(
            "SPIKE DETECTED: %s %s magnitude=%.2f price=%.5f",
            event.symbol, event.spike_type, event.magnitude, event.price,
        )
        for callback in self.alert_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error("Spike alert callback failed: %s", e)
    
    def get_spike_history(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
        events = list(self.spike_history)
        if symbol:
            events = [e for e in events if e.symbol == symbol]
        return [e.to_dict() for e in events[-limit:]]
    
    def get_spike_stats(self) -> Dict:
        events = list(self.spike_history)
        type_counts = {}
        for e in events:
            type_counts[e.spike_type] = type_counts.get(e.spike_type, 0) + 1
        
        return {
            'total_spikes': len(events),
            'by_type': type_counts,
            'avg_magnitude': float(np.mean([e.magnitude for e in events])) if events else 0,
        }


spike_detector = SpikeDetector()
