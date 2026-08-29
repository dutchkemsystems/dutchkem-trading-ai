from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from notifications.models import Notification, NotificationTemplate, UserNotificationPreference

User = get_user_model()


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )

    def test_create_notification(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test",
            notification_type="TRADE",
        )
        self.assertEqual(notification.title, "Test Notification")
        self.assertFalse(notification.is_read)

    def test_notification_str(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Trade Alert",
            message="Test",
            notification_type="TRADE",
        )
        self.assertIn("Trade Alert", str(notification))


class NotificationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)
        Notification.objects.create(
            user=self.user,
            title="Test",
            message="Test message",
            notification_type="TRADE",
        )

    def test_list_notifications(self):
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unread_count(self):
        response = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 1)

    def test_mark_all_read(self):
        response = self.client.post("/api/v1/notifications/read-all/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
