import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification, NotificationTemplate, UserNotificationPreference

logger = logging.getLogger("notifications")

User = get_user_model()


class NotificationService:
    """Service for sending notifications via email, SMS, and push"""

    def __init__(self):
        self.email_enabled = getattr(settings, "EMAIL_ALERTS_ENABLED", False)
        self.sms_enabled = getattr(settings, "SMS_ALERTS_ENABLED", False)
        self.push_enabled = getattr(settings, "PUSH_ALERTS_ENABLED", False)

    def send_notification(
        self,
        user,
        title: str,
        message: str,
        notification_type: str,
        priority: str = "NORMAL",
        data: Optional[Dict[str, Any]] = None,
        template_name: Optional[str] = None,
    ) -> Notification:
        """Create and send a notification via all enabled channels"""
        # Create notification record
        template = None
        if template_name:
            template = NotificationTemplate.objects.filter(name=template_name, is_active=True).first()

        notification = Notification.objects.create(
            user=user,
            template=template,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            data=data or {},
        )

        # Get user preferences
        prefs, _ = UserNotificationPreference.objects.get_or_create(user=user)

        # Check quiet hours
        if self._is_quiet_hours(prefs) and priority not in ("URGENT",):
            logger.info("Notification deferred (quiet hours): user=%s title=%s", user.username, title)
            return notification

        # Send email
        if self._should_send_email(notification_type, prefs):
            self._send_email(user, title, message, notification)

        # Send push notification
        if self._should_send_push(notification_type, prefs):
            self._send_push(user, title, message, notification)

        # Send SMS for critical alerts
        if priority == "URGENT" and prefs.sms_risk_alerts:
            self._send_sms(user, title, message, notification)

        return notification

    def _is_quiet_hours(self, prefs: UserNotificationPreference) -> bool:
        """Check if current time is within user's quiet hours"""
        if not prefs.quiet_hours_start or not prefs.quiet_hours_end:
            return False
        now = timezone.now().time()
        if prefs.quiet_hours_start <= prefs.quiet_hours_end:
            return prefs.quiet_hours_start <= now <= prefs.quiet_hours_end
        else:
            return now >= prefs.quiet_hours_start or now <= prefs.quiet_hours_end

    def _should_send_email(self, notification_type: str, prefs: UserNotificationPreference) -> bool:
        """Check if email should be sent for this notification type"""
        if not self.email_enabled:
            return False
        mapping = {
            "TRADE": prefs.email_trades,
            "SIGNAL": prefs.email_signals,
            "RISK": prefs.email_risk_alerts,
            "PAYMENT": prefs.email_payments,
        }
        return mapping.get(notification_type, True)

    def _should_send_push(self, notification_type: str, prefs: UserNotificationPreference) -> bool:
        """Check if push notification should be sent"""
        if not self.push_enabled:
            return False
        mapping = {
            "TRADE": prefs.push_trades,
            "SIGNAL": prefs.push_signals,
            "RISK": prefs.push_risk_alerts,
            "PAYMENT": prefs.push_payments,
        }
        return mapping.get(notification_type, True)

    def _send_email(self, user, title: str, message: str, notification: Notification) -> bool:
        """Send email notification"""
        if not user.email:
            return False
        try:
            send_mail(
                subject=f"[Dutchkem Trading] {title}",
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@dutchkem.com"),
                recipient_list=[user.email],
                fail_silently=True,
            )
            notification.sent_email = True
            notification.save(update_fields=["sent_email"])
            logger.info("Email notification sent: user=%s title=%s", user.username, title)
            return True
        except Exception as exc:
            logger.error("Email notification failed: user=%s err=%s", user.username, exc)
            return False

    def _send_push(self, user, title: str, message: str, notification: Notification) -> bool:
        """Send push notification (FCM/APNs)"""
        # Placeholder for push notification implementation
        # Integrate with Firebase Cloud Messaging or similar
        notification.sent_push = True
        notification.save(update_fields=["sent_push"])
        logger.info("Push notification sent: user=%s title=%s", user.username, title)
        return True

    def _send_sms(self, user, title: str, message: str, notification: Notification) -> bool:
        """Send SMS notification"""
        if not user.phone_number:
            return False
        # Placeholder for SMS integration (Termii, Africa's Talking, etc.)
        notification.sent_sms = True
        notification.save(update_fields=["sent_sms"])
        logger.info("SMS notification sent: user=%s title=%s", user.username, title)
        return True

    # === Convenience methods ===

    def notify_trade_executed(self, user, symbol: str, direction: str, volume: float, pnl: float):
        """Send trade execution notification"""
        emoji = "Profit" if pnl >= 0 else "Loss"
        return self.send_notification(
            user=user,
            title=f"Trade {emoji}: {direction} {volume} {symbol}",
            message=f"Your {direction} trade on {symbol} (volume: {volume}) has been executed. P&L: ${pnl:.2f}",
            notification_type="TRADE",
            priority="HIGH" if abs(pnl) > 100 else "NORMAL",
            data={"symbol": symbol, "direction": direction, "volume": volume, "pnl": pnl},
        )

    def notify_signal_generated(self, user, symbol: str, signal_type: str, strength: float, timeframe: str):
        """Send signal generation notification"""
        return self.send_notification(
            user=user,
            title=f"New {signal_type} Signal: {symbol}",
            message=f"A {signal_type} signal for {symbol} ({timeframe}) with {strength}% strength has been generated.",
            notification_type="SIGNAL",
            priority="HIGH" if strength > 80 else "NORMAL",
            data={"symbol": symbol, "signal_type": signal_type, "strength": strength, "timeframe": timeframe},
        )

    def notify_risk_alert(self, user, alert_type: str, message: str, severity: str = "HIGH"):
        """Send risk alert notification"""
        return self.send_notification(
            user=user,
            title=f"Risk Alert: {alert_type}",
            message=message,
            notification_type="RISK",
            priority="URGENT" if severity == "CRITICAL" else "HIGH",
            data={"alert_type": alert_type, "severity": severity},
        )

    def notify_payment(self, user, title: str, message: str, transaction_id: str, status: str):
        """Send payment notification"""
        return self.send_notification(
            user=user,
            title=title,
            message=message,
            notification_type="PAYMENT",
            priority="HIGH",
            data={"transaction_id": transaction_id, "status": status},
        )

    def notify_system(self, user, title: str, message: str, priority: str = "NORMAL"):
        """Send system notification"""
        return self.send_notification(
            user=user,
            title=title,
            message=message,
            notification_type="SYSTEM",
            priority=priority,
        )


notification_service = NotificationService()
