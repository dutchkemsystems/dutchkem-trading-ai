# Dutchkem Trading AI — Shared Indicator Utilities
# Extracted from timeframe_strategies.py to eliminate DRY violations

from typing import List, Tuple


def calculate_rsi(data: List[float], period: int = 14) -> float:
    """Calculate Relative Strength Index using Wilder's exponential smoothing.

    This uses the proper smoothed-average method (as described by Welles Wilder)
    instead of a simple moving average, which gives more accurate RSI values
    especially during trending markets.
    """
    if len(data) < period + 1:
        return 50.0

    # Calculate initial gains and losses
    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, len(data)):
        change = data[i] - data[i - 1]
        gains.append(max(0.0, change))
        losses.append(max(0.0, -change))

    # Seed with SMA of the first `period` values
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Wilder's smoothing: use (period-1)/period weighting for subsequent values
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_ema(data: List[float], period: int) -> float:
    """Calculate Exponential Moving Average"""
    if len(data) < period:
        return data[-1] if data else 0

    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period

    for price in data[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_macd(
    data: List[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[float, float, float]:
    """Calculate MACD, Signal Line, and Histogram
    
    Signal line is computed as the EMA of the MACD line itself,
    not just a copy of the MACD line.
    """
    # Calculate MACD line series
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    
    # For the signal line, we need the full MACD series
    # Build MACD series by computing EMA at each point
    macd_series = []
    if len(data) >= slow:
        # Initialize EMA values
        ema_fast_val = sum(data[:fast]) / fast
        ema_slow_val = sum(data[:slow]) / slow
        
        # Build series from slow period onward
        for i in range(slow, len(data)):
            # Update fast EMA
            if i == fast:
                ema_fast_val = sum(data[:fast]) / fast
            elif i > fast:
                k_fast = 2 / (fast + 1)
                ema_fast_val = data[i] * k_fast + ema_fast_val * (1 - k_fast)
            
            # Update slow EMA
            if i == slow:
                ema_slow_val = sum(data[:slow]) / slow
            else:
                k_slow = 2 / (slow + 1)
                ema_slow_val = data[i] * k_slow + ema_slow_val * (1 - k_slow)
            
            macd_series.append(ema_fast_val - ema_slow_val)
    
    # Signal line = EMA of MACD series
    if len(macd_series) >= signal:
        signal_line = calculate_ema(macd_series, signal)
    else:
        signal_line = macd_line  # Fallback if not enough data
    
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_stochastic(
    high: List[float], low: List[float], close: List[float],
    k_period: int = 14, d_period: int = 3, smooth: int = 3,
) -> Tuple[float, float]:
    """Calculate Stochastic Oscillator (%K, %D)
    
    %K is the raw stochastic value.
    %D is the SMA of %K over d_period (not just %K itself).
    """
    if len(high) < k_period:
        return 50, 50

    highest = max(high[-k_period:])
    lowest = min(low[-k_period:])

    if highest == lowest:
        k = 50
    else:
        k = ((close[-1] - lowest) / (highest - lowest)) * 100

    # Calculate %D as SMA of recent %K values over d_period
    k_values = []
    # We need d_period+1 full k_period windows ending at different points
    start = max(0, len(high) - k_period - d_period + 1)
    end = len(high) - k_period + 1  # exclusive — last full window ends at close[-1]
    for i in range(start, end):
        h_slice = high[i:i + k_period]
        l_slice = low[i:i + k_period]
        c_slice = close[i:i + k_period]
        if len(h_slice) >= k_period:
            h_max = max(h_slice)
            l_min = min(l_slice)
            if h_max != l_min:
                k_val = ((c_slice[-1] - l_min) / (h_max - l_min)) * 100
            else:
                k_val = 50
            k_values.append(k_val)
    
    if len(k_values) >= d_period:
        d = sum(k_values[-d_period:]) / d_period
    else:
        d = k  # Fallback
    
    return k, d


def calculate_bollinger(
    data: List[float], period: int = 20, std_dev: float = 2.0
) -> Tuple[float, float, float]:
    """Calculate Bollinger Bands (upper, middle, lower)"""
    if len(data) < period:
        return data[-1], data[-1], data[-1]

    sma = sum(data[-period:]) / period
    variance = sum((x - sma) ** 2 for x in data[-period:]) / period
    std = variance ** 0.5

    return sma + (std_dev * std), sma, sma - (std_dev * std)


def calculate_atr(
    high: List[float], low: List[float], close: List[float], period: int = 14
) -> float:
    """Calculate Average True Range using Wilder's exponential smoothing.

    Properly initializes with SMA of the first `period` true ranges, then
    applies Wilder's smoothing: ATR = (prev_ATR * (period-1) + TR) / period
    """
    if len(high) < period + 1:
        trs = []
        for i in range(1, len(high)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )
            trs.append(tr)
        return sum(trs) / len(trs) if trs else 0.0

    # Calculate true ranges
    trs: List[float] = []
    for i in range(1, len(high)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        trs.append(tr)

    # Seed with SMA of first `period` true ranges
    atr = sum(trs[:period]) / period

    # Wilder's smoothing
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period

    return atr


def calculate_adx(
    high: List[float], low: List[float], close: List[float], period: int = 14
) -> float:
    """Calculate Average Directional Index using Wilder's exponential smoothing."""
    if len(high) < period + 2:
        return 0.0

    plus_dm = []
    minus_dm = []
    trs = []

    for i in range(1, len(high)):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]

        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)

        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        trs.append(tr)

    if len(trs) < period:
        return 0.0

    # Wilder's smoothing for TR, +DM, -DM
    atr = sum(trs[:period]) / period
    plus_dm_smooth = sum(plus_dm[:period]) / period
    minus_dm_smooth = sum(minus_dm[:period]) / period

    dx_values = []
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        plus_dm_smooth = (plus_dm_smooth * (period - 1) + plus_dm[i]) / period
        minus_dm_smooth = (minus_dm_smooth * (period - 1) + minus_dm[i]) / period

        plus_di = (plus_dm_smooth / atr * 100) if atr > 0 else 0
        minus_di = (minus_dm_smooth / atr * 100) if atr > 0 else 0

        dx = (
            abs(plus_di - minus_di) / (plus_di + minus_di) * 100
            if (plus_di + minus_di) > 0
            else 0
        )
        dx_values.append(dx)

    # ADX = smoothed average of DX values (Wilder's smoothing)
    if len(dx_values) < period:
        return sum(dx_values) / len(dx_values) if dx_values else 0.0

    adx = sum(dx_values[:period]) / period
    for i in range(period, len(dx_values)):
        adx = (adx * (period - 1) + dx_values[i]) / period

    return adx


def calculate_cci(
    high: List[float], low: List[float], close: List[float], period: int = 20
) -> float:
    """Calculate Commodity Channel Index"""
    if len(high) < period:
        return 0

    tp = [(high[i] + low[i] + close[i]) / 3 for i in range(len(high))]
    sma = sum(tp[-period:]) / period
    mean_dev = sum(abs(tp[i] - sma) for i in range(-period, 0)) / period

    if mean_dev == 0:
        return 0

    return (tp[-1] - sma) / (0.015 * mean_dev)


def calculate_supertrend(
    high: List[float], low: List[float], close: List[float],
    period: int = 10, multiplier: float = 3.0,
) -> Tuple[float, int]:
    """Calculate Supertrend indicator (value, direction)"""
    if len(high) < period:
        return close[-1], 1

    atr = calculate_atr(high, low, close, period)
    hl2 = (high[-1] + low[-1]) / 2

    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    if close[-1] > upper_band:
        return lower_band, 1
    elif close[-1] < lower_band:
        return upper_band, -1

    return close[-1], 1


def calculate_ichimoku(
    high: List[float], low: List[float], close: List[float],
    tenkan: int = 9, kijun: int = 26, senkou: int = 52,
) -> dict:
    """Calculate Ichimoku Cloud components"""

    def midpoint(data: List[float], period: int) -> float:
        if len(data) < period:
            return data[-1]
        return (max(data[-period:]) + min(data[-period:])) / 2

    tenkan_sen = midpoint(high, tenkan)
    kijun_sen = midpoint(high, kijun)
    senkou_a = (tenkan_sen + kijun_sen) / 2
    senkou_b = midpoint(high, senkou)

    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
    }


def calculate_psar(
    high: List[float], low: List[float], close: List[float],
    af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.20,
) -> float:
    """Calculate Parabolic Stop and Reverse (PSAR) — full implementation.

    Uses the standard Wilder PSAR algorithm with acceleration factor ramping.
    Returns the current SAR value (reversal point).
    """
    n = len(high)
    if n < 2:
        return close[-1] if close else 0.0

    # Determine initial trend from first two bars
    is_long = close[1] > close[0]

    # Initialize
    sar = low[0] if is_long else high[0]
    ep = high[0] if is_long else low[0]  # extreme point
    af = af_start

    # Previous values for smoothing
    prev_sar = sar

    for i in range(1, n):
        # Calculate new SAR
        new_sar = prev_sar + af * (ep - prev_sar)

        # Enforce SAR constraint: must be within prior bar's range
        if is_long:
            # For long, SAR must be below prior low
            if i >= 2:
                new_sar = min(new_sar, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            else:
                new_sar = min(new_sar, low[i - 1])
        else:
            # For short, SAR must be above prior high
            if i >= 2:
                new_sar = max(new_sar, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            else:
                new_sar = max(new_sar, high[i - 1])

        # Check for reversal
        if is_long and low[i] < new_sar:
            # Reverse to short
            is_long = False
            new_sar = ep  # SAR = previous extreme point
            ep = low[i]
            af = af_start
        elif not is_long and high[i] > new_sar:
            # Reverse to long
            is_long = True
            new_sar = ep  # SAR = previous extreme point
            ep = high[i]
            af = af_start
        else:
            # No reversal — update extreme point and accelerate
            if is_long:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

        prev_sar = new_sar

    return prev_sar
