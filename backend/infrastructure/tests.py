"""
Tests for the infrastructure module — NodeHealth, FailoverEvent, AlertLog models.
"""
import pytest
from django.test import TestCase
from infrastructure.models import NodeHealth, FailoverEvent, AlertLog


class TestNodeHealthModel(TestCase):
    def setUp(self):
        self.node = NodeHealth.objects.create(
            node_id="node-1",
            host="192.168.1.100",
            port=14222,
            status="active",
            cpu_usage=45.2,
            memory_usage=62.8,
            disk_usage=30.1,
        )

    def test_create_node(self):
        self.assertEqual(self.node.node_id, "node-1")
        self.assertEqual(self.node.status, "active")
        self.assertEqual(self.node.host, "192.168.1.100")

    def test_node_str(self):
        self.assertIn("node-1", str(self.node))
        self.assertIn("active", str(self.node))

    def test_default_values(self):
        node = NodeHealth.objects.create(
            node_id="node-2", host="10.0.0.1"
        )
        self.assertEqual(node.status, "standby")
        self.assertEqual(node.cpu_usage, 0.0)
        self.assertEqual(node.memory_usage, 0.0)
        self.assertEqual(node.heartbeat_count, 0)
        self.assertEqual(node.failover_count, 0)

    def test_metadata_json(self):
        self.node.metadata = {"version": "1.0", "region": "us-east"}
        self.node.save()
        self.node.refresh_from_db()
        self.assertEqual(self.node.metadata["version"], "1.0")

    def test_unique_node_id(self):
        with self.assertRaises(Exception):
            NodeHealth.objects.create(
                node_id="node-1", host="10.0.0.2"
            )


class TestFailoverEventModel(TestCase):
    def test_create_event(self):
        event = FailoverEvent.objects.create(
            event_type="node_failure",
            source_node="node-1",
            target_node="node-2",
            severity="ERROR",
            description="Node 1 lost connectivity",
            duration_seconds=30.5,
            success=True,
        )
        self.assertEqual(event.event_type, "node_failure")
        self.assertEqual(event.severity, "ERROR")

    def test_event_str(self):
        event = FailoverEvent.objects.create(
            event_type="broker_failover",
            severity="WARNING",
            description="Broker failover triggered",
        )
        s = str(event)
        self.assertIn("broker_failover", s)
        self.assertIn("WARNING", s)

    def test_log_classmethod(self):
        event = FailoverEvent.log(
            event_type="leader_election",
            description="New leader elected",
            source_node="node-1",
            severity="INFO",
        )
        self.assertIsNotNone(event.pk)
        self.assertEqual(event.event_type, "leader_election")

    def test_metadata_default(self):
        event = FailoverEvent.objects.create(
            event_type="recovery",
            description="System recovered",
        )
        self.assertEqual(event.metadata, {})

    def test_success_default(self):
        event = FailoverEvent.objects.create(
            event_type="mt5_reconnect",
            description="MT5 reconnected",
        )
        self.assertTrue(event.success)


class TestAlertLogModel(TestCase):
    def test_create_alert(self):
        alert = AlertLog.objects.create(
            level="CRITICAL",
            channel="email",
            subject="Trading halted",
            message="Daily loss limit reached",
            recipient="admin@test.com",
        )
        self.assertEqual(alert.level, "CRITICAL")
        self.assertEqual(alert.status, "sent")

    def test_alert_str(self):
        alert = AlertLog.objects.create(
            level="WARNING",
            channel="telegram",
            subject="High drawdown",
            message="Drawdown exceeded 10%",
        )
        s = str(alert)
        self.assertIn("WARNING", s)
        self.assertIn("telegram", s)

    def test_log_classmethod(self):
        alert = AlertLog.log(
            level="INFO",
            channel="slack",
            subject="System started",
            message="All services running",
            recipient="#trading",
        )
        self.assertIsNotNone(alert.pk)
        self.assertEqual(alert.channel, "slack")

    def test_default_status(self):
        alert = AlertLog.objects.create(
            level="INFO",
            channel="webhook",
            subject="Test",
            message="Test message",
        )
        self.assertEqual(alert.status, "sent")

    def test_error_message(self):
        alert = AlertLog.objects.create(
            level="ERROR",
            channel="email",
            subject="Send failed",
            message="Alert could not be sent",
            status="failed",
            error_message="SMTP connection refused",
        )
        self.assertEqual(alert.status, "failed")
        self.assertIn("SMTP", alert.error_message)
