# Dutchkem Trading AI — Timeframe Strategies
# Multi-timeframe indicator strategies for M5, M15, M30, H1, H2, H4

from decimal import Decimal
from typing import Dict, Any, Optional


class TimeframeStrategy:
    """Base class for timeframe-specific strategies"""
    
    TIMEFRAME = None
    RISK_LEVEL = None
    TARGET_PIPS_MIN = 0
    TARGET_PIPS_MAX = 0
    STOP_LOSS_MIN = 0
    STOP_LOSS_MAX = 0
    
    def __init__(self):
        self.indicators = {}
        self.signals = []
    
    def calculate(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class M5ScalpingStrategy(TimeframeStrategy):
    """
    M5 Scalping Strategy — High Frequency
    Indicators: RSI (7), Stochastic (5,3,3), EMA Crossover (5,10)
    Target: 5-10 pips, SL: 10-15 pips
    """
    TIMEFRAME = 'M5'
    RISK_LEVEL = 'HIGH'
    TARGET_PIPS_MIN = 5
    TARGET_PIPS_MAX = 10
    STOP_LOSS_MIN = 10
    STOP_LOSS_MAX = 15
    
    def calculate(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        close = ohlcv_data.get('close', [])
        high = ohlcv_data.get('high', [])
        low = ohlcv_data.get('low', [])
        
        if len(close) < 20:
            return {'signal': 'NEUTRAL', 'strength': 0}
        
        # RSI (7-period for faster response)
        rsi = self._calculate_rsi(close, 7)
        
        # Stochastic (5,3,3)
        stoch_k, stoch_d = self._calculate_stochastic(high, low, close, 5, 3, 3)
        
        # EMA Crossover (5, 10)
        ema_fast = self._calculate_ema(close, 5)
        ema_slow = self._calculate_ema(close, 10)
        
        # Generate signal
        signal = 'NEUTRAL'
        strength = 0
        
        if rsi < 30 and stoch_k < 20 and ema_fast > ema_slow:
            signal = 'BUY'
            strength = min(100, (30 - rsi) + (20 - stoch_k) + ((ema_fast - ema_slow) * 1000))
        elif rsi > 70 and stoch_k > 80 and ema_fast < ema_slow:
            signal = 'SELL'
            strength = min(100, (rsi - 70) + (stoch_k - 80) + ((ema_slow - ema_fast) * 1000))
        
        return {
            'signal': signal,
            'strength': round(strength, 2),
            'indicators': {
                'rsi': round(rsi, 2),
                'stoch_k': round(stoch_k, 2),
                'stoch_d': round(stoch_d, 2),
                'ema_fast': round(ema_fast, 6),
                'ema_slow': round(ema_slow, 6)
            },
            'stop_loss_pips': self.STOP_LOSS_MIN,
            'take_profit_pips': self.TARGET_PIPS_MAX
        }
    
    def _calculate_rsi(self, data, period):
        gains = []
        losses = []
        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        
        if len(gains) < period:
            return 50
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_stochastic(self, high, low, close, k_period, d_period, smooth):
        if len(high) < k_period:
            return 50, 50
        
        highest = max(high[-k_period:])
        lowest = min(low[-k_period:])
        
        if highest == lowest:
            k = 50
        else:
            k = ((close[-1] - lowest) / (highest - lowest)) * 100
        
        d = k  # Simplified
        return k, d
    
    def _calculate_ema(self, data, period):
        if len(data) < period:
            return data[-1] if data else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema


class M15MomentumStrategy(TimeframeStrategy):
    """
    M15 Momentum Strategy — Short-term
    Indicators: MACD (12,26,9), Bollinger Bands (20,2), RSI (14)
    Target: 10-20 pips, SL: 15-25 pips
    """
    TIMEFRAME = 'M15'
    RISK_LEVEL = 'MEDIUM_HIGH'
    TARGET_PIPS_MIN = 10
    TARGET_PIPS_MAX = 20
    STOP_LOSS_MIN = 15
    STOP_LOSS_MAX = 25
    
    def calculate(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        close = ohlcv_data.get('close', [])
        high = ohlcv_data.get('high', [])
        low = ohlcv_data.get('low', [])
        
        if len(close) < 30:
            return {'signal': 'NEUTRAL', 'strength': 0}
        
        # MACD
        macd_line, signal_line, histogram = self._calculate_macd(close, 12, 26, 9)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger(close, 20, 2)
        
        # RSI (14)
        rsi = self._calculate_rsi(close, 14)
        
        # Generate signal
        signal = 'NEUTRAL'
        strength = 0
        
        if macd_line > signal_line and histogram > 0 and close[-1] < bb_middle and rsi < 60:
            signal = 'BUY'
            strength = min(100, ((macd_line - signal_line) * 10000) + (60 - rsi) + ((bb_middle - close[-1]) * 1000))
        elif macd_line < signal_line and histogram < 0 and close[-1] > bb_middle and rsi > 40:
            signal = 'SELL'
            strength = min(100, ((signal_line - macd_line) * 10000) + (rsi - 40) + ((close[-1] - bb_middle) * 1000))
        
        return {
            'signal': signal,
            'strength': round(strength, 2),
            'indicators': {
                'macd': round(macd_line, 6),
                'signal': round(signal_line, 6),
                'histogram': round(histogram, 6),
                'bb_upper': round(bb_upper, 6),
                'bb_middle': round(bb_middle, 6),
                'bb_lower': round(bb_lower, 6),
                'rsi': round(rsi, 2)
            },
            'stop_loss_pips': self.STOP_LOSS_MIN,
            'take_profit_pips': self.TARGET_PIPS_MAX
        }
    
    def _calculate_macd(self, data, fast, slow, signal):
        ema_fast = self._calculate_ema(data, fast)
        ema_slow = self._calculate_ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line  # Simplified
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger(self, data, period, std_dev):
        if len(data) < period:
            return data[-1], data[-1], data[-1]
        
        sma = sum(data[-period:]) / period
        variance = sum((x - sma) ** 2 for x in data[-period:]) / period
        std = variance ** 0.5
        
        return sma + (std_dev * std), sma, sma - (std_dev * std)
    
    def _calculate_ema(self, data, period):
        if len(data) < period:
            return data[-1] if data else 0
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def _calculate_rsi(self, data, period):
        gains = []
        losses = []
        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        if len(gains) < period:
            return 50
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))


class M30SwingStrategy(TimeframeStrategy):
    """
    M30 Swing Strategy — Medium-short term
    Indicators: Supertrend (10,3), ADX (14), CCI (20)
    Target: 20-40 pips, SL: 25-50 pips
    """
    TIMEFRAME = 'M30'
    RISK_LEVEL = 'MEDIUM'
    TARGET_PIPS_MIN = 20
    TARGET_PIPS_MAX = 40
    STOP_LOSS_MIN = 25
    STOP_LOSS_MAX = 50
    
    def calculate(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        close = ohlcv_data.get('close', [])
        high = ohlcv_data.get('high', [])
        low = ohlcv_data.get('low', [])
        
        if len(close) < 30:
            return {'signal': 'NEUTRAL', 'strength': 0}
        
        # Supertrend
        supertrend, direction = self._calculate_supertrend(high, low, close, 10, 3)
        
        # ADX
        adx = self._calculate_adx(high, low, close, 14)
        
        # CCI
        cci = self._calculate_cci(high, low, close, 20)
        
        # Generate signal
        signal = 'NEUTRAL'
        strength = 0
        
        if direction == 1 and adx > 25 and cci > 100:
            signal = 'BUY'
            strength = min(100, adx + (cci - 100) / 2)
        elif direction == -1 and adx > 25 and cci < -100:
            signal = 'SELL'
            strength = min(100, adx + (-100 - cci) / 2)
        
        return {
            'signal': signal,
            'strength': round(strength, 2),
            'indicators': {
                'supertrend': round(supertrend, 6),
                'direction': direction,
                'adx': round(adx, 2),
                'cci': round(cci, 2)
            },
            'stop_loss_pips': self.STOP_LOSS_MIN,
            'take_profit_pips': self.TARGET_PIPS_MAX
        }
    
    def _calculate_supertrend(self, high, low, close, period, multiplier):
        if len(high) < period:
            return close[-1], 1
        
        atr = self._calculate_atr(high, low, close, period)
        hl2 = (high[-1] + low[-1]) / 2
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        if close[-1] > upper_band:
            return lower_band, 1
        elif close[-1] < lower_band:
            return upper_band, -1
        
        return close[-1], 1
    
    def _calculate_atr(self, high, low, close, period):
        trs = []
        for i in range(1, len(high)):
            tr = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
            trs.append(tr)
        return sum(trs[-period:]) / period if trs else 0
    
    def _calculate_adx(self, high, low, close, period):
        if len(high) < period + 1:
            return 0
        
        plus_dm = []
        minus_dm = []
        trs = []
        
        for i in range(1, len(high)):
            up_move = high[i] - high[i-1]
            down_move = low[i-1] - low[i]
            
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
            
            tr = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
            trs.append(tr)
        
        atr = sum(trs[-period:]) / period
        plus_di = (sum(plus_dm[-period:]) / period / atr * 100) if atr > 0 else 0
        minus_di = (sum(minus_dm[-period:]) / period / atr * 100) if atr > 0 else 0
        
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
        return dx
    
    def _calculate_cci(self, high, low, close, period):
        if len(high) < period:
            return 0
        
        tp = [(high[i] + low[i] + close[i]) / 3 for i in range(len(high))]
        sma = sum(tp[-period:]) / period
        mean_dev = sum(abs(tp[i] - sma) for i in range(-period, 0)) / period
        
        if mean_dev == 0:
            return 0
        
        return (tp[-1] - sma) / (0.015 * mean_dev)


class H1TrendStrategy(TimeframeStrategy):
    """
    H1 Trend Strategy — Medium-term
    Indicators: Ichimoku Cloud, EMA (20,50,200), RSI (14)
    Target: 40-80 pips, SL: 50-100 pips
    """
    TIMEFRAME = 'H1'
    RISK_LEVEL = 'MEDIUM_LOW'
    TARGET_PIPS_MIN = 40
    TARGET_PIPS_MAX = 80
    STOP_LOSS_MIN = 50
    STOP_LOSS_MAX = 100
    
    def calculate(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        close = ohlcv_data.get('close', [])
        high = ohlcv_data.get('high', [])
        low = ohlcv_data.get('low', [])
        
        if len(close) < 200:
            return {'signal': 'NEUTRAL', 'strength': 0}
        
        # Ichimoku
        ichimoku = self._calculate_ichimoku(high, low, close, 9, 26, 52)
        
        # EMAs
        ema_20 = self._calculate_ema(close, 20)
        ema_50 = self._calculate_ema(close, 50)
        ema_200 = self._calculate_ema(close, 200)
        
        # RSI
        rsi = self._calculate_rsi(close, 14)
        
        # Generate signal
        signal = 'NEUTRAL'
        strength = 0
        
        if (close[-1] > ichimoku['senkou_a'] and 
            close[-1] > ichimoku['senkou_b'] and 
            ema_20 > ema_50 and 
            rsi > 50):
            signal = 'BUY'
            strength = min(100, (rsi - 50) + ((ema_20 - ema_50) * 1000))
        elif (close[-1] < ichimoku['senkou_a'] and 
              close[-1] < ichimoku['senkou_b'] and 
              ema_20 < ema_50 and 
              rsi < 50):
            signal = 'SELL'
            strength = min(100, (50 - rsi) + ((ema_50 - ema_20) * 1000))
        
        return {
            'signal': signal,
            'strength': round(strength, 2),
            'indicators': {
                'ichimoku': ichimoku,
                'ema_20': round(ema_20, 6),
                'ema_50': round(ema_50, 6),
                'ema_200': round(ema_200, 6),
                'rsi': round(rsi, 2)
            },
            'stop_loss_pips': self.STOP_LOSS_MIN,
            'take_profit_pips': self.TARGET_PIPS_MAX
        }
    
    def _calculate_ichimoku(self, high, low, close, tenkan, kijun, senkou):
        def midpoint(data, period):
            if len(data) < period:
                return data[-1]
            return (max(data[-period:]) + min(data[-period:])) / 2
        
        tenkan_sen = midpoint(high, tenkan)  # Simplified
        kijun_sen = midpoint(high, kijun)
        senkou_a = (tenkan_sen + kijun_sen) / 2
        senkou_b = midpoint(high, senkou)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b
        }
    
    def _calculate_ema(self, data, period):
        if len(data) < period:
            return data[-1] if data else 0
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def _calculate_rsi(self, data, period):
        gains = []
        losses = []
        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        if len(gains) < period:
            return 50
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))


class H2PositionStrategy(TimeframeStrategy):
    """
    H2 Position Strategy — Medium-long term
    Indicators: MACD (12,26,9), Parabolic SAR, ADX (14)
    Target: 80-150 pips, SL: 100-200 pips
    """
    TIMEFRAME = 'H2'
    RISK_LEVEL = 'LOW_MEDIUM'
    TARGET_PIPS_MIN = 80
    TARGET_PIPS_MAX = 150
    STOP_LOSS_MIN = 100
    STOP_LOSS_MAX = 200
    
    def calculate(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        close = ohlcv_data.get('close', [])
        high = ohlcv_data.get('high', [])
        low = ohlcv_data.get('low', [])
        
        if len(close) < 50:
            return {'signal': 'NEUTRAL', 'strength': 0}
        
        # MACD
        macd_line, signal_line, histogram = self._calculate_macd(close, 12, 26, 9)
        
        # Parabolic SAR
        psar = self._calculate_psar(high, low, close, 0.02, 0.2)
        
        # ADX
        adx = self._calculate_adx(high, low, close, 14)
        
        # Generate signal
        signal = 'NEUTRAL'
        strength = 0
        
        if macd_line > signal_line and psar < close[-1] and adx > 30:
            signal = 'BUY'
            strength = min(100, adx + ((macd_line - signal_line) * 10000))
        elif macd_line < signal_line and psar > close[-1] and adx > 30:
            signal = 'SELL'
            strength = min(100, adx + ((signal_line - macd_line) * 10000))
        
        return {
            'signal': signal,
            'strength': round(strength, 2),
            'indicators': {
                'macd': round(macd_line, 6),
                'signal': round(signal_line, 6),
                'histogram': round(histogram, 6),
                'psar': round(psar, 6),
                'adx': round(adx, 2)
            },
            'stop_loss_pips': self.STOP_LOSS_MIN,
            'take_profit_pips': self.TARGET_PIPS_MAX
        }
    
    def _calculate_macd(self, data, fast, slow, signal):
        ema_fast = self._calculate_ema(data, fast)
        ema_slow = self._calculate_ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _calculate_psar(self, high, low, close, af_start, af_step):
        if len(high) < 2:
            return close[-1]
        
        # Simplified PSAR
        psar = close[-1]
        return psar
    
    def _calculate_adx(self, high, low, close, period):
        if len(high) < period + 1:
            return 0
        
        plus_dm = []
        minus_dm = []
        trs = []
        
        for i in range(1, len(high)):
            up_move = high[i] - high[i-1]
            down_move = low[i-1] - low[i]
            
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
            
            tr = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
            trs.append(tr)
        
        atr = sum(trs[-period:]) / period
        plus_di = (sum(plus_dm[-period:]) / period / atr * 100) if atr > 0 else 0
        minus_di = (sum(minus_dm[-period:]) / period / atr * 100) if atr > 0 else 0
        
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
        return dx
    
    def _calculate_ema(self, data, period):
        if len(data) < period:
            return data[-1] if data else 0
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        return ema


class H4StrategicStrategy(TimeframeStrategy):
    """
    H4 Strategic Strategy — Long-term
    Indicators: Ichimoku Cloud, EMA (50,100,200), ATR (14)
    Target: 150-300 pips, SL: 200-400 pips
    """
    TIMEFRAME = 'H4'
    RISK_LEVEL = 'LOW'
    TARGET_PIPS_MIN = 150
    TARGET_PIPS_MAX = 300
    STOP_LOSS_MIN = 200
    STOP_LOSS_MAX = 400
    
    def calculate(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        close = ohlcv_data.get('close', [])
        high = ohlcv_data.get('high', [])
        low = ohlcv_data.get('low', [])
        
        if len(close) < 200:
            return {'signal': 'NEUTRAL', 'strength': 0}
        
        # Ichimoku
        ichimoku = self._calculate_ichimoku(high, low, close, 9, 26, 52)
        
        # EMAs
        ema_50 = self._calculate_ema(close, 50)
        ema_100 = self._calculate_ema(close, 100)
        ema_200 = self._calculate_ema(close, 200)
        
        # ATR
        atr = self._calculate_atr(high, low, close, 14)
        
        # Generate signal
        signal = 'NEUTRAL'
        strength = 0
        
        if (ema_50 > ema_200 and 
            close[-1] > ichimoku['senkou_a'] and 
            close[-1] > ichimoku['senkou_b']):
            signal = 'BUY'
            strength = min(100, ((ema_50 - ema_200) / ema_200 * 10000) + 50)
        elif (ema_50 < ema_200 and 
              close[-1] < ichimoku['senkou_a'] and 
              close[-1] < ichimoku['senkou_b']):
            signal = 'SELL'
            strength = min(100, ((ema_200 - ema_50) / ema_200 * 10000) + 50)
        
        return {
            'signal': signal,
            'strength': round(strength, 2),
            'indicators': {
                'ichimoku': ichimoku,
                'ema_50': round(ema_50, 6),
                'ema_100': round(ema_100, 6),
                'ema_200': round(ema_200, 6),
                'atr': round(atr, 6)
            },
            'stop_loss_pips': self.STOP_LOSS_MIN,
            'take_profit_pips': self.TARGET_PIPS_MAX
        }
    
    def _calculate_ichimoku(self, high, low, close, tenkan, kijun, senkou):
        def midpoint(data, period):
            if len(data) < period:
                return data[-1]
            return (max(data[-period:]) + min(data[-period:])) / 2
        
        tenkan_sen = midpoint(high, tenkan)
        kijun_sen = midpoint(high, kijun)
        senkou_a = (tenkan_sen + kijun_sen) / 2
        senkou_b = midpoint(high, senkou)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b
        }
    
    def _calculate_ema(self, data, period):
        if len(data) < period:
            return data[-1] if data else 0
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def _calculate_atr(self, high, low, close, period):
        trs = []
        for i in range(1, len(high)):
            tr = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
            trs.append(tr)
        return sum(trs[-period:]) / period if trs else 0


# Strategy Registry
TIMEFRAME_STRATEGIES = {
    'M5': M5ScalpingStrategy(),
    'M15': M15MomentumStrategy(),
    'M30': M30SwingStrategy(),
    'H1': H1TrendStrategy(),
    'H2': H2PositionStrategy(),
    'H4': H4StrategicStrategy(),
}


def get_strategy(timeframe: str) -> Optional[TimeframeStrategy]:
    """Get the strategy for a specific timeframe"""
    return TIMEFRAME_STRATEGIES.get(timeframe)


def calculate_signal(timeframe: str, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate signal for a specific timeframe"""
    strategy = get_strategy(timeframe)
    if strategy:
        return strategy.calculate(ohlcv_data)
    return {'signal': 'NEUTRAL', 'strength': 0, 'error': f'Unknown timeframe: {timeframe}'}
