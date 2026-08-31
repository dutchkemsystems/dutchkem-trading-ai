from django.test import TestCase
from unittest.mock import patch, MagicMock
from mcp_integration.services import MT5Service, CircuitBreaker


class CircuitBreakerTest(TestCase):
    def test_initial_state(self):
        cb = CircuitBreaker()
        self.assertEqual(cb.state, "closed")
        self.assertTrue(cb.allow_request())

    def test_opens_after_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        self.assertEqual(cb.state, "open")
        self.assertFalse(cb.allow_request())

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, "open")
        # With 0 timeout, should transition to half_open immediately
        self.assertTrue(cb.allow_request())
        self.assertEqual(cb.state, "half_open")

    def test_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        self.assertEqual(cb.state, "closed")
        self.assertEqual(cb.failure_count, 0)


class MT5ServiceTest(TestCase):
    def test_service_init(self):
        service = MT5Service()
        self.assertIsNotNone(service.circuit_breaker)
