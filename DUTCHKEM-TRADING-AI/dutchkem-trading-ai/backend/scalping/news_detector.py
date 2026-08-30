"""
V2 News Detector — Economic calendar integration, high-impact event detection, trading pause.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import deque
from enum import Enum

logger = logging.getLogger('scalping.news')


class NewsImpact(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class NewsEvent:
    def __init__(self, event_id: str, title: str, currency: str, impact: str, timestamp: datetime):
        self.event_id = event_id
        self.title = title
        self.currency = currency
        self.impact = impact
        self.timestamp = timestamp
        self.actual = None
        self.forecast = None
        self.previous = None
    
    def is_high_impact(self) -> bool:
        return self.impact == NewsImpact.HIGH.value
    
    def minutes_until(self) -> float:
        return (self.timestamp - datetime.now()).total_seconds() / 60
    
    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'title': self.title,
            'currency': self.currency,
            'impact': self.impact,
            'timestamp': self.timestamp.isoformat(),
            'minutes_until': round(self.minutes_until(), 1),
            'actual': self.actual,
            'forecast': self.forecast,
            'previous': self.previous,
        }


class NewsDetector:
    def __init__(self):
        self.events: deque = deque(maxlen=500)
        self.pre_news_pause_minutes = 30
        self.post_news_pause_minutes = 15
        self.high_impact_currencies = ['USD', 'EUR', 'GBP', 'JPY']
        self.active_pauses: Dict[str, datetime] = {}
        self.scheduled_events: List[NewsEvent] = []
    
    def add_event(self, event: NewsEvent):
        self.events.append(event)
        if event.is_high_impact():
            logger.info("High-impact news scheduled: %s (%s) at %s",
                       event.title, event.currency, event.timestamp)
    
    def should_pause_trading(self, symbol: str) -> Dict[str, Any]:
        now = datetime.now()
        
        if symbol in self.active_pauses:
            pause_until = self.active_pauses[symbol]
            if now < pause_until:
                remaining = (pause_until - now).total_seconds() / 60
                return {
                    'pause': True,
                    'reason': 'POST_NEWS_PAUSE',
                    'remaining_minutes': round(remaining, 1),
                }
            else:
                del self.active_pauses[symbol]
        
        for event in self.scheduled_events:
            if event.is_high_impact():
                currency = event.currency
                if currency in symbol:
                    minutes_until = event.minutes_until()
                    
                    if 0 < minutes_until <= self.pre_news_pause_minutes:
                        return {
                            'pause': True,
                            'reason': 'PRE_NEWS_PAUSE',
                            'event': event.title,
                            'minutes_until': round(minutes_until, 1),
                        }
                    
                    if -self.post_news_pause_minutes <= minutes_until <= 0:
                        pause_end = now + timedelta(minutes=self.post_news_pause_minutes)
                        self.active_pauses[symbol] = pause_end
                        return {
                            'pause': True,
                            'reason': 'POST_NEWS_PAUSE',
                            'event': event.title,
                            'remaining_minutes': self.post_news_pause_minutes,
                        }
        
        return {'pause': False}
    
    def get_upcoming_events(self, hours: float = 24.0) -> List[Dict]:
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        
        upcoming = [
            e for e in self.scheduled_events
            if now <= e.timestamp <= cutoff
        ]
        upcoming.sort(key=lambda e: e.timestamp)
        return [e.to_dict() for e in upcoming[:20]]
    
    def get_news_stats(self) -> Dict:
        high_impact = [e for e in self.events if e.is_high_impact()]
        return {
            'total_events': len(self.events),
            'high_impact_events': len(high_impact),
            'active_pauses': len(self.active_pauses),
            'scheduled_events': len(self.scheduled_events),
        }


news_detector = NewsDetector()
