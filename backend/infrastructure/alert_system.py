"""
V4 Alert System — Multi-channel alerting for critical events.
"""
import json
import logging
import os
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from collections import deque

logger = logging.getLogger('infrastructure.alert_system')

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False


class AlertLevel(Enum):
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class AlertChannel(Enum):
    EMAIL = 'email'
    TELEGRAM = 'telegram'
    SLACK = 'slack'
    WEBHOOK = 'webhook'


class AlertSystem:
    """
    Multi-channel alert system.
    - Email alerts
    - Telegram alerts
    - Slack alerts
    - Webhook alerts
    - Alert levels: INFO, WARNING, ERROR, CRITICAL
    """

    def __init__(self):
        self.config = {
            'email': {
                'enabled': False,
                'smtp_host': os.environ.get('ALERT_SMTP_HOST', 'smtp.gmail.com'),
                'smtp_port': int(os.environ.get('ALERT_SMTP_PORT', 587)),
                'smtp_user': os.environ.get('ALERT_SMTP_USER', ''),
                'smtp_password': os.environ.get('ALERT_SMTP_PASSWORD', ''),
                'from_email': os.environ.get('ALERT_FROM_EMAIL', ''),
                'to_emails': os.environ.get('ALERT_TO_EMAILS', '').split(','),
                'use_tls': True,
            },
            'telegram': {
                'enabled': False,
                'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
                'chat_id': os.environ.get('TELEGRAM_CHAT_ID', ''),
            },
            'slack': {
                'enabled': False,
                'webhook_url': os.environ.get('SLACK_WEBHOOK_URL', ''),
                'channel': os.environ.get('SLACK_CHANNEL', '#alerts'),
            },
            'webhook': {
                'enabled': False,
                'url': os.environ.get('ALERT_WEBHOOK_URL', ''),
                'headers': {'Content-Type': 'application/json'},
            },
        }

        self.alert_log: deque = deque(maxlen=1000)
        self.alert_history: deque = deque(maxlen=500)
        self._lock = threading.Lock()
        self._min_level = AlertLevel.WARNING
        self._rate_limit_seconds = 60
        self._last_alerts: Dict[str, float] = {}

        self._load_config_from_env()

    def _load_config_from_env(self):
        """Load configuration from environment variables."""
        if self.config['email']['smtp_user']:
            self.config['email']['enabled'] = True
        if self.config['telegram']['bot_token']:
            self.config['telegram']['enabled'] = True
        if self.config['slack']['webhook_url']:
            self.config['slack']['enabled'] = True
        if self.config['webhook']['url']:
            self.config['webhook']['enabled'] = True

    def set_minimum_level(self, level: AlertLevel):
        """Set the minimum alert level to send."""
        self._min_level = level

    def configure_email(self, smtp_host: str, smtp_port: int, smtp_user: str,
                        smtp_password: str, from_email: str, to_emails: List[str],
                        use_tls: bool = True):
        """Configure email alerting."""
        self.config['email'] = {
            'enabled': True,
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_user': smtp_user,
            'smtp_password': smtp_password,
            'from_email': from_email,
            'to_emails': to_emails,
            'use_tls': use_tls,
        }
        logger.info("Email alerting configured")

    def configure_telegram(self, bot_token: str, chat_id: str):
        """Configure Telegram alerting."""
        self.config['telegram'] = {
            'enabled': True,
            'bot_token': bot_token,
            'chat_id': chat_id,
        }
        logger.info("Telegram alerting configured")

    def configure_slack(self, webhook_url: str, channel: str = '#alerts'):
        """Configure Slack alerting."""
        self.config['slack'] = {
            'enabled': True,
            'webhook_url': webhook_url,
            'channel': channel,
        }
        logger.info("Slack alerting configured")

    def configure_webhook(self, url: str, headers: Optional[Dict] = None):
        """Configure webhook alerting."""
        self.config['webhook'] = {
            'enabled': True,
            'url': url,
            'headers': headers or {'Content-Type': 'application/json'},
        }
        logger.info("Webhook alerting configured")

    def send_alert(self, level: AlertLevel, subject: str, message: str,
                   channels: Optional[List[AlertChannel]] = None,
                   metadata: Optional[Dict] = None) -> Dict[str, bool]:
        """Send an alert through specified channels."""
        if not self._should_send(level):
            return {}

        if self._is_rate_limited(subject):
            logger.debug("Alert rate limited: %s", subject)
            return {}

        results = {}
        target_channels = channels or self._get_enabled_channels()

        for channel in target_channels:
            try:
                if channel == AlertChannel.EMAIL:
                    results['email'] = self._send_email(subject, message, level)
                elif channel == AlertChannel.TELEGRAM:
                    results['telegram'] = self._send_telegram(subject, message, level)
                elif channel == AlertChannel.SLACK:
                    results['slack'] = self._send_slack(subject, message, level)
                elif channel == AlertChannel.WEBHOOK:
                    results['webhook'] = self._send_webhook(subject, message, level, metadata)
            except Exception as e:
                logger.error("Failed to send alert via %s: %s", channel.value, e)
                results[channel.value] = False

        self._log_alert(level, subject, message, results, metadata)
        return results

    def _should_send(self, level: AlertLevel) -> bool:
        """Check if the alert level meets the minimum threshold."""
        levels = [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.ERROR, AlertLevel.CRITICAL]
        return levels.index(level) >= levels.index(self._min_level)

    def _is_rate_limited(self, subject: str) -> bool:
        """Check if the alert is rate limited."""
        now = time.time()
        if subject in self._last_alerts:
            if now - self._last_alerts[subject] < self._rate_limit_seconds:
                return True
        self._last_alerts[subject] = now
        return False

    def _get_enabled_channels(self) -> List[AlertChannel]:
        """Get list of enabled alert channels."""
        channels = []
        if self.config['email']['enabled']:
            channels.append(AlertChannel.EMAIL)
        if self.config['telegram']['enabled']:
            channels.append(AlertChannel.TELEGRAM)
        if self.config['slack']['enabled']:
            channels.append(AlertChannel.SLACK)
        if self.config['webhook']['enabled']:
            channels.append(AlertChannel.WEBHOOK)
        return channels

    def _send_email(self, subject: str, message: str, level: AlertLevel) -> bool:
        """Send email alert."""
        if not SMTP_AVAILABLE:
            logger.warning("SMTP not available for email alerts")
            return False

        config = self.config['email']
        try:
            level_emoji = {
                AlertLevel.INFO: 'ℹ️',
                AlertLevel.WARNING: '⚠️',
                AlertLevel.ERROR: '❌',
                AlertLevel.CRITICAL: '🚨',
            }

            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])
            msg['Subject'] = f"{level_emoji.get(level, '')} [{level.value}] {subject}"

            html = f"""
            <html>
            <body>
                <h2 style="color: {'#ff0000' if level == AlertLevel.CRITICAL else '#ff8800' if level == AlertLevel.ERROR else '#ffaa00'}">
                    [{level.value}] {subject}
                </h2>
                <p>{message}</p>
                <hr>
                <small>DutchKem Trading AI Alert System - {datetime.utcnow().isoformat()}</small>
            </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
                if config['use_tls']:
                    server.starttls()
                server.login(config['smtp_user'], config['smtp_password'])
                server.send_message(msg)

            logger.info("Email alert sent: %s", subject)
            return True
        except Exception as e:
            logger.error("Email alert failed: %s", e)
            return False

    def _send_telegram(self, subject: str, message: str, level: AlertLevel) -> bool:
        """Send Telegram alert."""
        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not available for Telegram alerts")
            return False

        config = self.config['telegram']
        try:
            level_emoji = {
                AlertLevel.INFO: 'ℹ️',
                AlertLevel.WARNING: '⚠️',
                AlertLevel.ERROR: '❌',
                AlertLevel.CRITICAL: '🚨',
            }

            text = (
                f"{level_emoji.get(level, '')} *[{level.value}] {subject}*\n\n"
                f"{message}\n\n"
                f"_DutchKem Trading AI - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_"
            )

            url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
            payload = {
                'chat_id': config['chat_id'],
                'text': text,
                'parse_mode': 'Markdown',
            }

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram alert sent: %s", subject)
                return True
            else:
                logger.error("Telegram alert failed: %s", response.text)
                return False
        except Exception as e:
            logger.error("Telegram alert failed: %s", e)
            return False

    def _send_slack(self, subject: str, message: str, level: AlertLevel) -> bool:
        """Send Slack alert."""
        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not available for Slack alerts")
            return False

        config = self.config['slack']
        try:
            level_color = {
                AlertLevel.INFO: '#36a64f',
                AlertLevel.WARNING: '#ff9900',
                AlertLevel.ERROR: '#ff0000',
                AlertLevel.CRITICAL: '#cc0000',
            }

            payload = {
                'channel': config['channel'],
                'attachments': [{
                    'color': level_color.get(level, '#999999'),
                    'title': f'[{level.value}] {subject}',
                    'text': message,
                    'footer': f'DutchKem Trading AI - {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}',
                }],
            }

            response = requests.post(config['webhook_url'], json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Slack alert sent: %s", subject)
                return True
            else:
                logger.error("Slack alert failed: %s", response.text)
                return False
        except Exception as e:
            logger.error("Slack alert failed: %s", e)
            return False

    def _send_webhook(self, subject: str, message: str, level: AlertLevel,
                      metadata: Optional[Dict] = None) -> bool:
        """Send webhook alert."""
        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not available for webhook alerts")
            return False

        config = self.config['webhook']
        try:
            payload = {
                'level': level.value,
                'subject': subject,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'dutchkem-trading-ai',
                'metadata': metadata or {},
            }

            response = requests.post(
                config['url'],
                json=payload,
                headers=config['headers'],
                timeout=10
            )
            if response.status_code < 400:
                logger.info("Webhook alert sent: %s", subject)
                return True
            else:
                logger.error("Webhook alert failed: %s", response.text)
                return False
        except Exception as e:
            logger.error("Webhook alert failed: %s", e)
            return False

    def _log_alert(self, level: AlertLevel, subject: str, message: str,
                   results: Dict[str, bool], metadata: Optional[Dict] = None):
        """Log alert to database."""
        try:
            from .models import AlertLog
            for channel, success in results.items():
                AlertLog.log(
                    level=level.value,
                    channel=channel,
                    subject=subject,
                    message=message,
                    status='sent' if success else 'failed',
                    metadata=metadata or {},
                )
        except Exception as e:
            logger.error("Failed to log alert to DB: %s", e)

    def get_status(self) -> Dict[str, Any]:
        """Get current alert system status."""
        return {
            'channels': {
                channel.value: config['enabled']
                for channel, config in [
                    (AlertChannel.EMAIL, self.config['email']),
                    (AlertChannel.TELEGRAM, self.config['telegram']),
                    (AlertChannel.SLACK, self.config['slack']),
                    (AlertChannel.WEBHOOK, self.config['webhook']),
                ]
            },
            'minimum_level': self._min_level.value,
            'enabled_channels': [c.value for c in self._get_enabled_channels()],
            'total_alerts_sent': len(self.alert_log),
        }


_alert_system: Optional[AlertSystem] = None


def get_alert_system() -> AlertSystem:
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system
