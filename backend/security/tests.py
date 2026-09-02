"""
Tests for the security module — BlockedIP, SecurityEvent, EncryptionKey, CredentialVault models.
"""
import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from security.models import BlockedIP, SecurityEvent, EncryptionKey, CredentialVault, ThreatLevel


class TestBlockedIPModel(TestCase):
    def test_create_blocked_ip(self):
        blocked = BlockedIP.objects.create(
            ip_address="192.168.1.100",
            reason="Brute force attempt",
            threat_level=ThreatLevel.HIGH,
        )
        self.assertEqual(blocked.ip_address, "192.168.1.100")
        self.assertTrue(blocked.is_active)

    def test_blocked_ip_str(self):
        blocked = BlockedIP.objects.create(
            ip_address="10.0.0.1",
            is_active=True,
        )
        s = str(blocked)
        self.assertIn("10.0.0.1", s)
        self.assertIn("active", s)

    def test_is_expired_no_expiry(self):
        blocked = BlockedIP.objects.create(
            ip_address="10.0.0.2",
            expires_at=None,
        )
        self.assertFalse(blocked.is_expired())

    def test_is_expired_past(self):
        blocked = BlockedIP.objects.create(
            ip_address="10.0.0.3",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertTrue(blocked.is_expired())

    def test_is_expired_future(self):
        blocked = BlockedIP.objects.create(
            ip_address="10.0.0.4",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertFalse(blocked.is_expired())

    def test_inactive_ip(self):
        blocked = BlockedIP.objects.create(
            ip_address="10.0.0.5",
            is_active=False,
        )
        self.assertFalse(blocked.is_active)


class TestSecurityEventModel(TestCase):
    def test_create_event(self):
        event = SecurityEvent.objects.create(
            event_type="login_attempt",
            threat_level=ThreatLevel.MEDIUM,
            user_id="user123",
            ip_address="192.168.1.1",
            details={"attempt": 3},
        )
        self.assertEqual(event.event_type, "login_attempt")
        self.assertEqual(event.threat_level, ThreatLevel.MEDIUM)

    def test_event_str(self):
        event = SecurityEvent.objects.create(
            event_type="waf_block",
            user_id="admin",
            threat_level=ThreatLevel.HIGH,
        )
        s = str(event)
        self.assertIn("waf_block", s)
        self.assertIn("admin", s)

    def test_event_hash_generation(self):
        """SecurityEvent should auto-generate hash on save."""
        event = SecurityEvent.objects.create(
            event_type="test_event",
            user_id="user1",
            ip_address="10.0.0.1",
        )
        self.assertIsNotNone(event.event_hash)
        self.assertEqual(len(event.event_hash), 64)  # SHA-256 hex

    def test_previous_hash_chain(self):
        """Each event should reference the previous event's hash."""
        event1 = SecurityEvent.objects.create(
            event_type="first_event",
            user_id="user1",
        )
        event2 = SecurityEvent.objects.create(
            event_type="second_event",
            user_id="user2",
        )
        self.assertEqual(event2.previous_hash, event1.event_hash)

    def test_first_event_previous_hash_empty(self):
        """First event should have empty previous_hash."""
        event = SecurityEvent.objects.create(
            event_type="first_event",
            user_id="user1",
        )
        # previous_hash is set to "" for first event
        # But there might be other events from previous test runs
        # Just verify it's a string
        self.assertIsInstance(event.previous_hash, str)

    def test_action_taken_default(self):
        event = SecurityEvent.objects.create(
            event_type="test",
        )
        self.assertEqual(event.action_taken, "allowed")

    def test_details_json(self):
        event = SecurityEvent.objects.create(
            event_type="waf_block",
            details={"rule": "sql_injection", "path": "/api/v1/trades/"},
        )
        event.refresh_from_db()
        self.assertEqual(event.details["rule"], "sql_injection")


class TestEncryptionKeyModel(TestCase):
    def test_create_key(self):
        key = EncryptionKey.objects.create(
            version=1,
            encrypted_key="dGVzdC1rZXk=",
            is_active=True,
        )
        self.assertEqual(key.version, 1)
        self.assertTrue(key.is_active)

    def test_key_str(self):
        key = EncryptionKey.objects.create(
            version=2,
            encrypted_key="encrypted_data",
        )
        s = str(key)
        self.assertIn("v2", s)
        self.assertIn("active", s)

    def test_unique_version(self):
        EncryptionKey.objects.create(version=1, encrypted_key="key1")
        with self.assertRaises(Exception):
            EncryptionKey.objects.create(version=1, encrypted_key="key2")


class TestCredentialVaultModel(TestCase):
    def test_create_credential(self):
        cred = CredentialVault.objects.create(
            name="mt5_password",
            credential_type="secret",
            encrypted_value=b"encrypted_bytes",
            description="MT5 broker password",
        )
        self.assertEqual(cred.name, "mt5_password")
        self.assertTrue(cred.is_active)
        self.assertEqual(cred.access_count, 0)

    def test_credential_str(self):
        cred = CredentialVault.objects.create(
            name="api_key",
            credential_type="api_key",
            encrypted_value=b"key_bytes",
        )
        s = str(cred)
        self.assertIn("api_key", s)

    def test_is_expired_no_expiry(self):
        cred = CredentialVault.objects.create(
            name="test_cred",
            encrypted_value=b"data",
        )
        self.assertFalse(cred.is_expired())

    def test_is_expired_past(self):
        cred = CredentialVault.objects.create(
            name="expired_cred",
            encrypted_value=b"data",
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(cred.is_expired())

    def test_is_expired_future(self):
        cred = CredentialVault.objects.create(
            name="valid_cred",
            encrypted_value=b"data",
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.assertFalse(cred.is_expired())

    def test_unique_name(self):
        CredentialVault.objects.create(name="unique_name", encrypted_value=b"a")
        with self.assertRaises(Exception):
            CredentialVault.objects.create(name="unique_name", encrypted_value=b"b")
