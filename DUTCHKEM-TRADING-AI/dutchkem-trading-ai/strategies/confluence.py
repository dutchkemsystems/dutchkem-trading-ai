# Dutchkem Trading AI — Multi-Timeframe Confluence Scoring System
# Analyzes signals across all timeframes to generate high-confidence trade signals

from decimal import Decimal
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class SignalDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class ConfluenceLevel(Enum):
    STRONG = "STRONG"       # 80-100%
    MODERATE = "MODERATE"   # 60-79%
    WEAK = "WEAK"           # 40-59%
    NONE = "NONE"           # 0-39%


@dataclass
class TimeframeSignal:
    timeframe: str
    signal_type: str
    strength: Decimal
    indicators: Dict[str, Any]
    stop_loss_pips: int
    take_profit_pips: int


@dataclass
class ConfluenceResult:
    symbol: str
    direction: SignalDirection
    total_score: Decimal
    confluence_level: ConfluenceLevel
    timeframe_scores: Dict[str, Decimal]
    timeframe_signals: Dict[str, TimeframeSignal]
    higher_tf_agreement: bool
    all_tf_aligned: bool
    recommended_entry: Optional[Decimal]
    recommended_sl: Optional[int]
    recommended_tp: Optional[int]
    risk_reward_ratio: Decimal
    confidence: Decimal


class MultiTimeframeConfluence:
    """
    Multi-Timeframe Confluence Scoring System
    
    Analyzes signals across 6 timeframes (M5, M15, M30, H1, H2, H4)
    to generate high-confidence trade signals.
    
    Timeframe Weights:
    - H4: 30% (Strategic direction)
    - H2: 25% (Position trend)
    - H1: 20% (Trend confirmation)
    - M30: 10% (Swing entry)
    - M15: 10% (Momentum confirmation)
    - M5: 5% (Entry timing)
    """
    
    TIMEFRAME_WEIGHTS = {
        'H4': Decimal('0.30'),   # Strategic direction
        'H2': Decimal('0.25'),   # Position trend
        'H1': Decimal('0.20'),   # Trend confirmation
        'M30': Decimal('0.10'),  # Swing entry
        'M15': Decimal('0.10'),  # Momentum confirmation
        'M5': Decimal('0.05'),   # Entry timing
    }
    
    TIMEFRAME_ORDER = ['H4', 'H2', 'H1', 'M30', 'M15', 'M5']
    
    def __init__(self):
        self.min_confluence_score = Decimal('60')  # Minimum 60% for signal
        self.strong_confluence_score = Decimal('80')  # Strong signal threshold
    
    def calculate_confluence(
        self,
        symbol: str,
        timeframe_signals: Dict[str, TimeframeSignal]
    ) -> ConfluenceResult:
        """
        Calculate multi-timeframe confluence score
        
        Args:
            symbol: Trading symbol
            timeframe_signals: Dict of timeframe -> TimeframeSignal
            
        Returns:
            ConfluenceResult with score and recommendation
        """
        # Calculate individual timeframe scores
        timeframe_scores = {}
        for tf in self.TIMEFRAME_ORDER:
            if tf in timeframe_signals:
                signal = timeframe_signals[tf]
                score = self._calculate_timeframe_score(signal)
                timeframe_scores[tf] = score
            else:
                timeframe_scores[tf] = Decimal('0')
        
        # Calculate weighted total score
        total_score = self._calculate_weighted_score(timeframe_scores)
        
        # Determine direction
        direction = self._determine_direction(timeframe_signals)
        
        # Check higher timeframe agreement
        higher_tf_agreement = self._check_higher_tf_agreement(timeframe_signals)
        
        # Check all timeframes aligned
        all_tf_aligned = self._check_all_tf_aligned(timeframe_signals)
        
        # Calculate confluence level
        confluence_level = self._get_confluence_level(total_score)
        
        # Get recommended entry/SL/TP
        entry, sl, tp = self._get_recommendations(timeframe_signals, direction)
        
        # Calculate risk-reward ratio
        risk_reward = Decimal('0')
        if sl and tp and sl > 0:
            risk_reward = Decimal(str(tp)) / Decimal(str(sl))
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            total_score, higher_tf_agreement, all_tf_aligned, risk_reward
        )
        
        return ConfluenceResult(
            symbol=symbol,
            direction=direction,
            total_score=total_score,
            confluence_level=confluence_level,
            timeframe_scores=timeframe_scores,
            timeframe_signals=timeframe_signals,
            higher_tf_agreement=higher_tf_agreement,
            all_tf_aligned=all_tf_aligned,
            recommended_entry=entry,
            recommended_sl=sl,
            recommended_tp=tp,
            risk_reward_ratio=risk_reward,
            confidence=confidence
        )
    
    def _calculate_timeframe_score(self, signal: TimeframeSignal) -> Decimal:
        """Calculate score for a single timeframe"""
        base_score = signal.strength
        
        # Bonus for strong signals
        if signal.signal_type in ['STRONG_BUY', 'STRONG_SELL']:
            base_score += Decimal('10')
        
        # Bonus for good risk-reward
        if signal.take_profit_pips > 0 and signal.stop_loss_pips > 0:
            rr = Decimal(str(signal.take_profit_pips)) / Decimal(str(signal.stop_loss_pips))
            if rr >= Decimal('2'):
                base_score += Decimal('5')
        
        return min(base_score, Decimal('100'))
    
    def _calculate_weighted_score(self, timeframe_scores: Dict[str, Decimal]) -> Decimal:
        """Calculate weighted total score"""
        total = Decimal('0')
        weight_sum = Decimal('0')
        
        for tf, score in timeframe_scores.items():
            weight = self.TIMEFRAME_WEIGHTS.get(tf, Decimal('0'))
            total += score * weight
            weight_sum += weight
        
        if weight_sum > 0:
            return total / weight_sum
        return Decimal('0')
    
    def _determine_direction(self, signals: Dict[str, TimeframeSignal]) -> SignalDirection:
        """Determine overall direction from signals"""
        long_score = Decimal('0')
        short_score = Decimal('0')
        
        for tf, signal in signals.items():
            weight = self.TIMEFRAME_WEIGHTS.get(tf, Decimal('0'))
            if signal.signal_type in ['BUY', 'STRONG_BUY']:
                long_score += signal.strength * weight
            elif signal.signal_type in ['SELL', 'STRONG_SELL']:
                short_score += signal.strength * weight
        
        if long_score > short_score and long_score > Decimal('30'):
            return SignalDirection.LONG
        elif short_score > long_score and short_score > Decimal('30'):
            return SignalDirection.SHORT
        
        return SignalDirection.NEUTRAL
    
    def _check_higher_tf_agreement(self, signals: Dict[str, TimeframeSignal]) -> bool:
        """Check if higher timeframes (H4, H2, H1) agree on direction"""
        higher_tfs = ['H4', 'H2', 'H1']
        directions = []
        
        for tf in higher_tfs:
            if tf in signals:
                signal = signals[tf]
                if signal.signal_type in ['BUY', 'STRONG_BUY']:
                    directions.append('LONG')
                elif signal.signal_type in ['SELL', 'STRONG_SELL']:
                    directions.append('SHORT')
                else:
                    directions.append('NEUTRAL')
        
        # All must agree and not be neutral
        if len(directions) == 3 and len(set(directions)) == 1 and directions[0] != 'NEUTRAL':
            return True
        
        return False
    
    def _check_all_tf_aligned(self, signals: Dict[str, TimeframeSignal]) -> bool:
        """Check if all timeframes are aligned"""
        directions = []
        
        for tf in self.TIMEFRAME_ORDER:
            if tf in signals:
                signal = signals[tf]
                if signal.signal_type in ['BUY', 'STRONG_BUY']:
                    directions.append('LONG')
                elif signal.signal_type in ['SELL', 'STRONG_SELL']:
                    directions.append('SHORT')
                else:
                    directions.append('NEUTRAL')
        
        # All must agree and not be neutral
        if len(directions) == len(self.TIMEFRAME_ORDER) and len(set(directions)) == 1 and directions[0] != 'NEUTRAL':
            return True
        
        return False
    
    def _get_confluence_level(self, score: Decimal) -> ConfluenceLevel:
        """Get confluence level from score"""
        if score >= self.strong_confluence_score:
            return ConfluenceLevel.STRONG
        elif score >= self.min_confluence_score:
            return ConfluenceLevel.MODERATE
        elif score >= Decimal('40'):
            return ConfluenceLevel.WEAK
        return ConfluenceLevel.NONE
    
    def _get_recommendations(
        self,
        signals: Dict[str, TimeframeSignal],
        direction: SignalDirection
    ) -> tuple:
        """Get recommended entry, SL, TP from signals"""
        if direction == SignalDirection.NEUTRAL:
            return None, None, None
        
        # Use M15 for entry timing, H1 for SL/TP
        entry_signal = signals.get('M15') or signals.get('M30')
        sl_signal = signals.get('H1') or signals.get('H2')
        
        entry = None
        sl = None
        tp = None
        
        if entry_signal:
            # Use stop_loss and take_profit from the signal
            sl = entry_signal.stop_loss_pips
            tp = entry_signal.take_profit_pips
        
        if sl_signal and not sl:
            sl = sl_signal.stop_loss_pips
            tp = sl_signal.take_profit_pips
        
        # Ensure minimum 1:2 risk-reward
        if sl and tp and sl > 0:
            min_tp = sl * 2
            if tp < min_tp:
                tp = min_tp
        
        return entry, sl, tp
    
    def _calculate_confidence(
        self,
        total_score: Decimal,
        higher_tf_agreement: bool,
        all_tf_aligned: bool,
        risk_reward: Decimal
    ) -> Decimal:
        """Calculate confidence level"""
        confidence = total_score
        
        # Bonus for higher TF agreement
        if higher_tf_agreement:
            confidence += Decimal('10')
        
        # Bonus for all TF aligned
        if all_tf_aligned:
            confidence += Decimal('15')
        
        # Bonus for good risk-reward
        if risk_reward >= Decimal('2'):
            confidence += Decimal('5')
        
        return min(confidence, Decimal('100'))
    
    def should_trade(self, result: ConfluenceResult) -> bool:
        """Determine if we should trade based on confluence result"""
        # Must have minimum confluence
        if result.total_score < self.min_confluence_score:
            return False
        
        # Must not be neutral
        if result.direction == SignalDirection.NEUTRAL:
            return False
        
        # Must have acceptable risk-reward
        if result.risk_reward_ratio < Decimal('1.5'):
            return False
        
        return True
    
    def get_trade_setup(self, result: ConfluenceResult) -> Dict[str, Any]:
        """Get complete trade setup from confluence result"""
        if not self.should_trade(result):
            return None
        
        return {
            'symbol': result.symbol,
            'direction': result.direction.value,
            'confluence_score': str(result.total_score),
            'confluence_level': result.confluence_level.value,
            'entry_price': str(result.recommended_entry) if result.recommended_entry else 'MARKET',
            'stop_loss_pips': result.recommended_sl,
            'take_profit_pips': result.recommended_tp,
            'risk_reward_ratio': str(result.risk_reward_ratio),
            'confidence': str(result.confidence),
            'higher_tf_agreement': result.higher_tf_agreement,
            'all_tf_aligned': result.all_tf_aligned,
            'timeframe_scores': {tf: str(score) for tf, score in result.timeframe_scores.items()},
            'risk_per_trade': '1%',
            'max_position_size': '1%'
        }


# Singleton instance
confluence_engine = MultiTimeframeConfluence()
