import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger("notifications")


class AlertService:
    def __init__(self):
        self.slack_webhook = getattr(settings, "SLACK_WEBHOOK_URL", "")
        self.telegram_bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
        self.email_enabled = getattr(settings, "EMAIL_ALERTS_ENABLED", False)

    def send_slack(self, message: str, level: str = "info"):
        if not self.slack_webhook:
            return

        color_map = {"info": "#36a64f", "warning": "#ff9900", "critical": "#ff0000", "success": "#36a64f"}
        payload = {
            "attachments": [{
                "color": color_map.get(level, "#36a64f"),
                "title": f"Dutchkem Trading AI - {level.upper()}",
                "text": message,
            }]
        }

        try:
            resp = requests.post(self.slack_webhook, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("Slack alert sent: %s", level)
        except requests.RequestException as exc:
            logger.error("Slack alert failed: %s", exc)

    def send_telegram(self, message: str):
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        try:
            resp = requests.post(url, json={
                "chat_id": self.telegram_chat_id,
                "text": f"🚨 Dutchkem Alert\n\n{message}",
                "parse_mode": "HTML",
            }, timeout=10)
            resp.raise_for_status()
            logger.info("Telegram alert sent")
        except requests.RequestException as exc:
            logger.error("Telegram alert failed: %s", exc)

    def alert_risk_limit(self, limit_type: str, current: float, threshold: float):
        message = (
            f"⚠️ *Risk Alert*: {limit_type}\n"
            f"Current: {current:.2f}%\n"
            f"Threshold: {threshold:.2f}%\n"
            f"Trading may be restricted."
        )
        self.send_slack(message, "warning")
        self.send_telegram(message)

    def alert_circuit_breaker(self, reason: str):
        message = f"🛑 *Circuit Breaker Triggered*\nReason: {reason}\nAll trading has been stopped."
        self.send_slack(message, "critical")
        self.send_telegram(message)

    def alert_trade_executed(self, symbol: str, direction: str, volume: float, pnl: float):
        emoji = "✅" if pnl >= 0 else "❌"
        message = (
            f"{emoji} *Trade Executed*\n"
            f"Symbol: {symbol}\nDirection: {direction}\n"
            f"Volume: {volume}\nP&L: ${pnl:.2f}"
        )
        self.send_slack(message, "success" if pnl >= 0 else "warning")

    def alert_daily_target_reached(self, pnl_percent: float, target: float):
        message = (
            f"🎯 *Daily Target Reached*\n"
            f"P&L: {pnl_percent:.2f}%\nTarget: {target:.2f}%\n"
            f"Trading stopped for the day."
        )
        self.send_slack(message, "success")
        self.send_telegram(message)

    def alert_system_error(self, component: str, error: str):
        message = f"🔴 *System Error*\nComponent: {component}\nError: {error}"
        self.send_slack(message, "critical")
        self.send_telegram(message)


alert_service = AlertService()
