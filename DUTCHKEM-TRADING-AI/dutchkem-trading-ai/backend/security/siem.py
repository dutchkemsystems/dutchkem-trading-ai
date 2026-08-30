"""
V5 Security Information & Event Management (SIEM) System.

Correlates security events, generates alerts, exports forensic data,
and maintains threat intelligence for the Dutchkem Trading AI platform.
"""
import json
import logging
import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

from .models import SecurityEvent, ThreatLevel

logger = logging.getLogger('security.siem')


# ---------------------------------------------------------------------------
# Correlation Rules
# ---------------------------------------------------------------------------

@dataclass
class CorrelationRule:
    name: str
    description: str
    pattern: str  # event_type prefix or keyword
    threshold: int  # trigger count within window
    time_window: int  # seconds
    threat_level: int = ThreatLevel.HIGH

    def matches(self, event: SecurityEvent) -> bool:
        return self.pattern.lower() in event.event_type.lower()


def _default_rules() -> List[CorrelationRule]:
    return [
        CorrelationRule(
            name='brute_force',
            description='Multiple failed login attempts from same source',
            pattern='login_failure',
            threshold=5,
            time_window=300,
            threat_level=ThreatLevel.CRITICAL,
        ),
        CorrelationRule(
            name='credential_stuffing',
            description='Login failures across many accounts from same IP',
            pattern='login_failure',
            threshold=10,
            time_window=600,
            threat_level=ThreatLevel.CRITICAL,
        ),
        CorrelationRule(
            name='api_abuse',
            description='Excessive API calls exceeding normal thresholds',
            pattern='rate_limit_exceeded',
            threshold=8,
            time_window=120,
            threat_level=ThreatLevel.HIGH,
        ),
        CorrelationRule(
            name='suspicious_trading',
            description='Unusual trading activity patterns detected',
            pattern='suspicious_trading',
            threshold=3,
            time_window=600,
            threat_level=ThreatLevel.HIGH,
        ),
        CorrelationRule(
            name='data_exfiltration',
            description='Large data downloads or unusual data access patterns',
            pattern='data_exfiltration',
            threshold=2,
            time_window=300,
            threat_level=ThreatLevel.CRITICAL,
        ),
        CorrelationRule(
            name='permission_denied',
            description='Repeated authorization failures',
            pattern='permission_denied',
            threshold=6,
            time_window=300,
            threat_level=ThreatLevel.HIGH,
        ),
        CorrelationRule(
            name='waf_block',
            description='Multiple web application firewall blocks',
            pattern='waf_block',
            threshold=5,
            time_window=300,
            threat_level=ThreatLevel.HIGH,
        ),
    ]


# ---------------------------------------------------------------------------
# Alert Manager
# ---------------------------------------------------------------------------

class AlertManager:
    """In-memory alert store with severity escalation and resolution."""

    def __init__(self):
        self._alerts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_alert(
        self,
        severity: int,
        title: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        alert_id = str(uuid.uuid4())
        alert = {
            'id': alert_id,
            'severity': severity,
            'title': title,
            'description': description,
            'details': details or {},
            'status': 'open',
            'created_at': timezone.now().isoformat(),
            'updated_at': timezone.now().isoformat(),
            'resolution': None,
        }
        with self._lock:
            self._alerts[alert_id] = alert
        logger.warning('ALERT [%s] %s — %s', severity, title, description)
        return alert

    def escalate_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert or alert['status'] != 'open':
                return None
            alert['severity'] = min(alert['severity'] + 1, ThreatLevel.CRITICAL)
            alert['updated_at'] = timezone.now().isoformat()
            return alert.copy()

    def resolve_alert(self, alert_id: str, resolution: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None
            alert['status'] = 'resolved'
            alert['resolution'] = resolution
            alert['updated_at'] = timezone.now().isoformat()
            return alert.copy()

    def get_open_alerts(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                a.copy() for a in self._alerts.values() if a['status'] == 'open'
            ]


# ---------------------------------------------------------------------------
# Threat Intelligence
# ---------------------------------------------------------------------------

class ThreatIntelligence:
    """Tracks known threats and IP reputation scores."""

    def __init__(self):
        self._known_threats: List[Dict[str, Any]] = [
            {'pattern': 'brute_force', 'description': 'Repeated login failures from single source', 'threat_level': ThreatLevel.CRITICAL},
            {'pattern': 'credential_stuffing', 'description': 'Automated credential testing', 'threat_level': ThreatLevel.CRITICAL},
            {'pattern': 'sql_injection', 'description': 'SQL injection attempt patterns', 'threat_level': ThreatLevel.HIGH},
            {'pattern': 'xss_attack', 'description': 'Cross-site scripting attempt', 'threat_level': ThreatLevel.HIGH},
            {'pattern': 'data_exfiltration', 'description': 'Unauthorized data extraction', 'threat_level': ThreatLevel.CRITICAL},
            {'pattern': 'privilege_escalation', 'description': 'Attempting to gain elevated access', 'threat_level': ThreatLevel.HIGH},
        ]
        self._ip_scores: Dict[str, int] = {}
        self._threat_feeds: List[Dict[str, Any]] = []

    def check_ip_reputation(self, ip: str) -> int:
        """Return reputation score 0-100 (100 = trusted, 0 = malicious)."""
        if ip in self._ip_scores:
            return self._ip_scores[ip]

        # Check events for this IP
        recent_failures = SecurityEvent.objects.filter(
            ip_address=ip,
            event_type='login_failure',
            timestamp__gte=timezone.now() - timedelta(hours=24),
        ).count()
        blocks = SecurityEvent.objects.filter(
            ip_address=ip,
            event_type='waf_block',
            timestamp__gte=timezone.now() - timedelta(hours=24),
        ).count()

        score = max(0, 100 - (recent_failures * 10) - (blocks * 15))
        self._ip_scores[ip] = score
        return score

    def get_known_threats(self) -> List[Dict[str, Any]]:
        return list(self._known_threats)

    def update_threat_feed(self, feed_data: List[Dict[str, Any]]) -> None:
        for entry in feed_data:
            self._threat_feeds.append(entry)
            if 'ip' in entry and 'score' in entry:
                self._ip_scores[entry['ip']] = entry['score']
        logger.info('Threat feed updated: %d entries added', len(feed_data))


# ---------------------------------------------------------------------------
# Forensic Exporter
# ---------------------------------------------------------------------------

class ForensicExporter:
    """Export security events and user activity for forensic analysis."""

    def export_events(
        self,
        start: timezone.datetime,
        end: timezone.datetime,
        fmt: str = 'json',
    ) -> str:
        events = SecurityEvent.objects.filter(
            timestamp__gte=start, timestamp__lte=end
        ).order_by('timestamp')

        data = []
        for ev in events:
            data.append({
                'id': ev.id,
                'timestamp': ev.timestamp.isoformat(),
                'event_type': ev.event_type,
                'threat_level': ev.threat_level,
                'user_id': ev.user_id,
                'ip_address': ev.ip_address,
                'details': ev.details,
                'endpoint': ev.endpoint,
                'method': ev.method,
                'action_taken': ev.action_taken,
                'event_hash': ev.event_hash,
                'previous_hash': ev.previous_hash,
            })

        if fmt == 'json':
            return json.dumps(data, indent=2, default=str)
        elif fmt == 'csv':
            if not data:
                return ''
            headers = ','.join(data[0].keys())
            rows = [','.join(str(v) for v in row.values()) for row in data]
            return headers + '\n' + '\n'.join(rows)
        return json.dumps(data, default=str)

    def export_user_activity(
        self,
        user_id: str,
        start: timezone.datetime,
        end: timezone.datetime,
    ) -> List[Dict[str, Any]]:
        events = SecurityEvent.objects.filter(
            user_id=user_id,
            timestamp__gte=start,
            timestamp__lte=end,
        ).order_by('timestamp')

        return [
            {
                'id': ev.id,
                'timestamp': ev.timestamp.isoformat(),
                'event_type': ev.event_type,
                'threat_level': ev.threat_level,
                'ip_address': ev.ip_address,
                'details': ev.details,
                'action_taken': ev.action_taken,
            }
            for ev in events
        ]

    def generate_incident_report(self, incident_id: str) -> Dict[str, Any]:
        events = SecurityEvent.objects.filter(
            details__incident_id=incident_id
        ).order_by('timestamp')

        events_data = [
            {
                'id': ev.id,
                'timestamp': ev.timestamp.isoformat(),
                'event_type': ev.event_type,
                'threat_level': ev.threat_level,
                'user_id': ev.user_id,
                'ip_address': ev.ip_address,
                'details': ev.details,
            }
            for ev in events
        ]

        threat_counts = Counter(ev.event_type for ev in events)
        max_threat = max((ev.threat_level for ev in events), default=ThreatLevel.INFO)

        return {
            'incident_id': incident_id,
            'total_events': len(events_data),
            'max_threat_level': max_threat,
            'event_breakdown': dict(threat_counts),
            'first_seen': events_data[0]['timestamp'] if events_data else None,
            'last_seen': events_data[-1]['timestamp'] if events_data else None,
            'events': events_data,
        }


# ---------------------------------------------------------------------------
# SIEM Engine (Singleton)
# ---------------------------------------------------------------------------

class SIEMEngine:
    """Central SIEM engine — correlates events, generates alerts, exports data."""

    _instance: Optional['SIEMEngine'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialised = False
            return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self._initialised = True

        self.rules: List[CorrelationRule] = _default_rules()
        self.alert_manager = AlertManager()
        self.threat_intel = ThreatIntelligence()
        self.forensic = ForensicExporter()

        self._event_buffer: List[SecurityEvent] = []
        self._alert_buffer: List[Dict[str, Any]] = []
        self._engine_lock = threading.Lock()

        logger.info('SIEM engine initialised with %d correlation rules', len(self.rules))

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def process_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        threat_level: int = ThreatLevel.INFO,
        user_id: str = '',
        ip_address: Optional[str] = None,
    ) -> SecurityEvent:
        """Persist a security event and run correlation."""
        event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            endpoint=details.get('endpoint', ''),
            method=details.get('method', ''),
            action_taken=details.get('action_taken', 'allowed'),
        )
        event.save()

        with self._engine_lock:
            self._event_buffer.append(event)

        # Correlate against rules
        self._evaluate_rules(event)

        return event

    def correlate_events(
        self,
        events: Optional[List[SecurityEvent]] = None,
        time_window: int = 300,
    ) -> List[Dict[str, Any]]:
        """Detect multi-step attacks by grouping related events within a time window."""
        if events is None:
            since = timezone.now() - timedelta(seconds=time_window)
            events = list(SecurityEvent.objects.filter(
                timestamp__gte=since
            ).order_by('timestamp'))

        if not events:
            return []

        # Group by ip_address + user_id
        groups: Dict[str, List[SecurityEvent]] = defaultdict(list)
        for ev in events:
            key = f"{ev.ip_address or 'unknown'}:{ev.user_id or 'unknown'}"
            groups[key].append(ev)

        correlated: List[Dict[str, Any]] = []
        for key, group in groups.items():
            if len(group) < 2:
                continue

            types = [ev.event_type for ev in group]
            unique_types = set(types)

            # Check if multiple different event types → multi-step
            if len(unique_types) >= 2:
                correlated.append({
                    'source_key': key,
                    'event_count': len(group),
                    'event_types': list(unique_types),
                    'time_span_seconds': (
                        group[-1].timestamp - group[0].timestamp
                    ).total_seconds(),
                    'first_event': group[0].id,
                    'last_event': group[-1].id,
                    'threat_level': max(ev.threat_level for ev in group),
                })

        return correlated

    def generate_alert(self, event: SecurityEvent) -> Dict[str, Any]:
        """Create an alert from a security event."""
        severity_labels = {
            ThreatLevel.INFO: 'Info',
            ThreatLevel.LOW: 'Low',
            ThreatLevel.MEDIUM: 'Medium',
            ThreatLevel.HIGH: 'High',
            ThreatLevel.CRITICAL: 'Critical',
        }

        title = f"[{severity_labels.get(event.threat_level, 'Unknown')}] {event.event_type}"
        description = (
            f"Security event '{event.event_type}' detected. "
            f"IP: {event.ip_address or 'N/A'}. "
            f"User: {event.user_id or 'N/A'}."
        )

        recommended_action = self._recommended_action(event)

        alert = self.alert_manager.create_alert(
            severity=event.threat_level,
            title=title,
            description=description,
            details={
                'event_id': event.id,
                'event_type': event.event_type,
                'ip_address': event.ip_address,
                'user_id': event.user_id,
                'recommended_action': recommended_action,
            },
        )

        with self._engine_lock:
            self._alert_buffer.append(alert)

        return alert

    def get_threat_summary(self, time_range: str = '24h') -> Dict[str, Any]:
        """Aggregated threat statistics for the given time range."""
        hours = self._parse_time_range(time_range)
        since = timezone.now() - timedelta(hours=hours)

        events = SecurityEvent.objects.filter(timestamp__gte=since)
        total = events.count()

        type_counts = Counter(ev.event_type for ev in events)
        level_counts = Counter(ev.threat_level for ev in events)
        ip_counts = Counter(ev.ip_address for ev in events if ev.ip_address)

        return {
            'time_range': time_range,
            'total_events': total,
            'by_type': dict(type_counts),
            'by_threat_level': {str(k): v for k, v in level_counts.items()},
            'top_source_ips': dict(ip_counts.most_common(10)),
            'generated_at': timezone.now().isoformat(),
        }

    def export_events(
        self,
        start: timezone.datetime,
        end: timezone.datetime,
        fmt: str = 'json',
    ) -> str:
        return self.forensic.export_events(start, end, fmt)

    def get_realtime_alerts(self) -> List[Dict[str, Any]]:
        """Return recent high-priority open alerts (MEDIUM+)."""
        open_alerts = self.alert_manager.get_open_alerts()
        return [
            a for a in open_alerts
            if a['severity'] >= ThreatLevel.MEDIUM
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate_rules(self, event: SecurityEvent) -> None:
        for rule in self.rules:
            if not rule.matches(event):
                continue

            since = timezone.now() - timedelta(seconds=rule.time_window)
            count = SecurityEvent.objects.filter(
                event_type=event.event_type,
                ip_address=event.ip_address,
                timestamp__gte=since,
            ).count()

            if count >= rule.threshold:
                logger.warning(
                    'Rule "%s" triggered: %d events of type "%s" from %s in %ds',
                    rule.name, count, rule.event_type, event.ip_address, rule.time_window,
                )
                alert = self.generate_alert(event)
                alert['rule'] = rule.name
                alert['matched_count'] = count

    def _recommended_action(self, event: SecurityEvent) -> str:
        actions = {
            'login_failure': 'Monitor account; consider temporary lockout after threshold',
            'login_success': 'Log for audit',
            'rate_limit_enforced': 'Review rate-limit thresholds; block persistent offenders',
            'waf_block': 'Review WAF rule; consider IP ban',
            'suspicious_trading': 'Freeze account; manual review required',
            'data_exfiltration': 'Isolate affected systems; forensic investigation',
            'permission_denied': 'Audit user permissions; remove unnecessary access',
            'ids_alert': 'Investigate alert; correlate with other events',
        }
        return actions.get(event.event_type, 'Review event details manually')

    @staticmethod
    def _parse_time_range(time_range: str) -> int:
        mapping = {'1h': 1, '6h': 6, '12h': 12, '24h': 24, '7d': 168, '30d': 720}
        return mapping.get(time_range, 24)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_siem_instance: Optional[SIEMEngine] = None


def get_siem() -> SIEMEngine:
    global _siem_instance
    if _siem_instance is None:
        _siem_instance = SIEMEngine()
    return _siem_instance
