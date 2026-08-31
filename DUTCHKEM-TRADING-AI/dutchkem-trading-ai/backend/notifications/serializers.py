from rest_framework import serializers

from .models import Notification, NotificationTemplate, UserNotificationPreference


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "template_type",
            "subject",
            "body_template",
            "email_template",
            "push_template",
            "sms_template",
            "is_active",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "template",
            "title",
            "message",
            "notification_type",
            "priority",
            "data",
            "is_read",
            "read_at",
            "sent_email",
            "sent_push",
            "sent_sms",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationPreference
        fields = [
            "id",
            "user",
            "email_trades",
            "email_signals",
            "email_risk_alerts",
            "email_payments",
            "push_trades",
            "push_signals",
            "push_risk_alerts",
            "push_payments",
            "sms_risk_alerts",
            "quiet_hours_start",
            "quiet_hours_end",
        ]
        read_only_fields = ["id", "user"]
