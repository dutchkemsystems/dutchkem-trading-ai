import hashlib
import hmac
import json
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from payments.models import KYCVerification, PaymentGateway, Transaction
from payments.services import PaymentService

User = get_user_model()


@pytest.fixture
def korapay_gateway(db):
    return PaymentGateway.objects.create(
        name="KORAPAY",
        display_name="Korapay",
        is_active=True,
        supports_deposits=True,
        supports_withdrawals=True,
        min_deposit=100,
        max_deposit=10000000,
        min_withdrawal=500,
        max_withdrawal=5000000,
        deposit_fee_percent=Decimal("1.5"),
        withdrawal_fee_percent=Decimal("2.0"),
        deposit_processing_time="Instant",
        withdrawal_processing_time="1-3 Business Days",
        supported_currencies=["NGN", "GHS", "KES", "ZAR"],
        supported_channels=["card", "bank_transfer", "ussd", "mobile_money"],
    )


@pytest.fixture
def verified_kyc(test_user):
    return KYCVerification.objects.create(
        user=test_user,
        level="FULL",
        status="VERIFIED",
        document_type="NIN",
        document_number="12345678901",
        submitted_at=timezone.now(),
        verified_at=timezone.now(),
    )


@pytest.mark.django_db
class TestPaymentGatewayModel:
    def test_create_gateway(self, korapay_gateway):
        assert korapay_gateway.name == "KORAPAY"
        assert korapay_gateway.is_active
        assert korapay_gateway.supports_deposits
        assert "NGN" in korapay_gateway.supported_currencies
        assert "card" in korapay_gateway.supported_channels

    def test_gateway_str(self, korapay_gateway):
        assert str(korapay_gateway) == "Korapay"

    def test_gateway_default_fees(self, db):
        gw = PaymentGateway.objects.create(
            name="KORAPAY", display_name="Korapay Test", is_active=True,
        )
        assert gw.deposit_fee_percent == Decimal("0")
        assert gw.withdrawal_fee_percent == Decimal("0")


@pytest.mark.django_db
class TestTransactionModel:
    def test_create_deposit(self, test_user, korapay_gateway):
        tx = Transaction.objects.create(
            user=test_user,
            transaction_type="DEPOSIT",
            amount=Decimal("5000"),
            currency="NGN",
            gateway=korapay_gateway,
            korapay_ref="DK-TEST123",
            fee=Decimal("75"),
            net_amount=Decimal("4925"),
            status="PENDING",
        )
        assert tx.transaction_type == "DEPOSIT"
        assert tx.amount == Decimal("5000")
        assert tx.status == "PENDING"
        assert tx.korapay_ref == "DK-TEST123"

    def test_transaction_str(self, test_user, korapay_gateway):
        tx = Transaction.objects.create(
            user=test_user,
            transaction_type="DEPOSIT",
            amount=Decimal("10000"),
            currency="NGN",
            gateway=korapay_gateway,
            korapay_ref="DK-TEST456",
            fee=Decimal("150"),
            net_amount=Decimal("9850"),
            status="PENDING",
        )
        assert "DEPOSIT" in str(tx)
        assert "10000" in str(tx)

    def test_transaction_ordering(self, test_user, korapay_gateway):
        tx1 = Transaction.objects.create(
            user=test_user, transaction_type="DEPOSIT",
            amount=Decimal("1000"), currency="NGN",
            gateway=korapay_gateway, korapay_ref="DK-1",
            fee=Decimal("0"), net_amount=Decimal("1000"),
            status="COMPLETED",
        )
        tx2 = Transaction.objects.create(
            user=test_user, transaction_type="DEPOSIT",
            amount=Decimal("2000"), currency="NGN",
            gateway=korapay_gateway, korapay_ref="DK-2",
            fee=Decimal("0"), net_amount=Decimal("2000"),
            status="PENDING",
        )
        txs = list(Transaction.objects.filter(user=test_user))
        assert txs[0].korapay_ref == "DK-2"
        assert txs[1].korapay_ref == "DK-1"


@pytest.mark.django_db
class TestKorapayGateway:
    @patch("payments.gateways.korapay.requests")
    def test_initialize_transaction_success(self, mock_requests, korapay_gateway):
        from payments.gateways.korapay import KorapayGateway

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.korapay.com/test",
                "reference": "DK-TEST123",
                "access_code": "access_code_123",
            },
        }
        mock_resp.raise_for_status = MagicMock()
        mock_requests.request.return_value = mock_resp

        gw = KorapayGateway()
        result = gw.initialize_transaction(
            amount=5000,
            currency="NGN",
            reference="DK-TEST123",
            customer_email="test@test.com",
            customer_name="Test User",
        )
        assert result["status"] is True
        assert "authorization_url" in result["data"]

    @patch("payments.gateways.korapay.requests")
    def test_initialize_transaction_failure(self, mock_requests):
        from payments.gateways.korapay import KorapayGateway

        mock_requests.request.side_effect = Exception("Connection failed")
        gw = KorapayGateway()
        result = gw.initialize_transaction(
            amount=5000,
            currency="NGN",
            reference="DK-FAIL",
            customer_email="test@test.com",
        )
        assert result["status"] is False
        assert "message" in result

    def test_unsupported_currency(self):
        from payments.gateways.korapay import KorapayGateway

        gw = KorapayGateway()
        result = gw.initialize_transaction(
            amount=5000,
            currency="USD",
            reference="DK-USD",
            customer_email="test@test.com",
        )
        assert result["status"] is False
        assert "Unsupported currency" in result["message"]

    @patch("payments.gateways.korapay.requests")
    def test_verify_transaction_success(self, mock_requests):
        from payments.gateways.korapay import KorapayGateway

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": True,
            "data": {
                "reference": "DK-TEST123",
                "status": "success",
                "amount": 5000,
                "currency": "NGN",
                "channel": "card",
            },
        }
        mock_resp.raise_for_status = MagicMock()
        mock_requests.request.return_value = mock_resp

        gw = KorapayGateway()
        result = gw.verify_transaction("DK-TEST123")
        assert result["status"] is True
        assert result["data"]["status"] == "success"

    def test_webhook_signature_verification(self):
        from payments.gateways.korapay import KorapayGateway

        gw = KorapayGateway()
        gw.webhook_secret = "test_secret"
        body = b'{"event":"payment.success"}'
        signature = hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()
        assert gw.verify_webhook_signature(body, signature) is True
        assert gw.verify_webhook_signature(body, "wrong_signature") is False

    def test_parse_webhook_event(self):
        from payments.gateways.korapay import KorapayGateway

        gw = KorapayGateway()
        body = {
            "event": "payment.success",
            "data": {
                "reference": "DK-TEST123",
                "status": "success",
                "amount": 5000,
                "currency": "NGN",
                "channel": "card",
                "metadata": {"user_id": "123"},
                "paid_at": "2026-01-01T00:00:00Z",
            },
        }
        result = gw.parse_webhook_event(body)
        assert result["event_type"] == "payment.success"
        assert result["reference"] == "DK-TEST123"
        assert result["amount"] == 5000.0
        assert result["channel"] == "card"


@pytest.mark.django_db
class TestPaymentService:
    @patch("payments.services.KorapayGateway")
    def test_create_deposit_success(self, mock_cls, test_user, korapay_gateway):
        mock_instance = MagicMock()
        mock_instance.initialize_transaction.return_value = {
            "status": True,
            "data": {"authorization_url": "https://checkout.korapay.com/test"},
        }
        mock_cls.return_value = mock_instance

        service = PaymentService()
        tx = service.create_deposit(
            user=test_user,
            amount=Decimal("5000"),
            currency="NGN",
            redirect_url="http://localhost:3000/payments/callback",
        )
        assert tx.status == "PROCESSING"
        assert tx.transaction_type == "DEPOSIT"
        assert tx.amount == Decimal("5000")
        assert tx.currency == "NGN"
        assert tx.korapay_ref.startswith("DK-")

    @patch("payments.services.KorapayGateway")
    def test_create_deposit_fee_calculation(self, mock_cls, test_user, korapay_gateway):
        mock_instance = MagicMock()
        mock_instance.initialize_transaction.return_value = {"status": True, "data": {}}
        mock_cls.return_value = mock_instance

        service = PaymentService()
        tx = service.create_deposit(
            user=test_user,
            amount=Decimal("10000"),
            currency="NGN",
        )
        expected_fee = Decimal("10000") * (Decimal("1.5") / Decimal("100"))
        assert tx.fee == expected_fee
        assert tx.net_amount == Decimal("10000") - expected_fee

    def test_create_deposit_insufficient_amount(self, test_user, korapay_gateway):
        service = PaymentService()
        with pytest.raises(ValueError, match="Minimum deposit"):
            service.create_deposit(user=test_user, amount=Decimal("50"), currency="NGN")

    def test_create_deposit_unsupported_currency(self, test_user, korapay_gateway):
        service = PaymentService()
        with pytest.raises(ValueError, match="Unsupported currency"):
            service.create_deposit(user=test_user, amount=Decimal("5000"), currency="USD")

    @patch("payments.services.KorapayGateway")
    def test_create_deposit_init_failure(self, mock_cls, test_user, korapay_gateway):
        mock_instance = MagicMock()
        mock_instance.initialize_transaction.return_value = {"status": False, "message": "Failed"}
        mock_cls.return_value = mock_instance

        service = PaymentService()
        tx = service.create_deposit(user=test_user, amount=Decimal("5000"), currency="NGN")
        assert tx.status == "FAILED"

    @patch("payments.services.KorapayGateway")
    def test_verify_deposit_success(self, mock_cls, test_user, korapay_gateway):
        tx = Transaction.objects.create(
            user=test_user,
            transaction_type="DEPOSIT",
            amount=Decimal("5000"),
            currency="NGN",
            gateway=korapay_gateway,
            korapay_ref="DK-VERIFY-TEST",
            fee=Decimal("75"),
            net_amount=Decimal("4925"),
            status="PROCESSING",
        )

        mock_instance = MagicMock()
        mock_instance.verify_transaction.return_value = {
            "status": True,
            "data": {"status": "success", "channel": "card"},
        }
        mock_cls.return_value = mock_instance

        service = PaymentService()
        result = service.verify_deposit("DK-VERIFY-TEST")
        assert result.status == "COMPLETED"
        assert result.completed_at is not None

        test_user.refresh_from_db()
        assert test_user.balance == Decimal("4925")

    @patch("payments.services.KorapayGateway")
    def test_verify_deposit_already_completed(self, mock_cls, test_user, korapay_gateway):
        tx = Transaction.objects.create(
            user=test_user,
            transaction_type="DEPOSIT",
            amount=Decimal("5000"),
            currency="NGN",
            gateway=korapay_gateway,
            korapay_ref="DK-COMPLETE",
            fee=Decimal("75"),
            net_amount=Decimal("4925"),
            status="COMPLETED",
            completed_at=timezone.now(),
        )

        service = PaymentService()
        result = service.verify_deposit("DK-COMPLETE")
        assert result.status == "COMPLETED"
        mock_cls.return_value.verify_transaction.assert_not_called()

    def test_verify_deposit_not_found(self, test_user):
        service = PaymentService()
        with pytest.raises(Transaction.DoesNotExist):
            service.verify_deposit("DK-NONEXISTENT")

    @patch("payments.services.KorapayGateway")
    def test_handle_webhook_success(self, mock_cls, test_user, korapay_gateway):
        tx = Transaction.objects.create(
            user=test_user,
            transaction_type="DEPOSIT",
            amount=Decimal("5000"),
            currency="NGN",
            gateway=korapay_gateway,
            korapay_ref="DK-WEBHOOK-1",
            fee=Decimal("75"),
            net_amount=Decimal("4925"),
            status="PROCESSING",
        )

        service = PaymentService()
        result = service.handle_webhook({
            "event_type": "payment.success",
            "reference": "DK-WEBHOOK-1",
            "channel": "card",
        })
        assert result["status"] == "ok"

        tx.refresh_from_db()
        assert tx.status == "COMPLETED"
        assert tx.completed_at is not None

    def test_handle_webhook_unknown_reference(self, test_user):
        service = PaymentService()
        result = service.handle_webhook({
            "event_type": "payment.success",
            "reference": "DK-UNKNOWN",
        })
        assert result["status"] == "error"

    @patch("payments.services.KorapayGateway")
    def test_handle_webhook_failed(self, mock_cls, test_user, korapay_gateway):
        tx = Transaction.objects.create(
            user=test_user,
            transaction_type="DEPOSIT",
            amount=Decimal("5000"),
            currency="NGN",
            gateway=korapay_gateway,
            korapay_ref="DK-WEBHOOK-FAIL",
            fee=Decimal("75"),
            net_amount=Decimal("4925"),
            status="PROCESSING",
        )

        service = PaymentService()
        result = service.handle_webhook({
            "event_type": "payment.failed",
            "reference": "DK-WEBHOOK-FAIL",
        })
        assert result["status"] == "ok"

        tx.refresh_from_db()
        assert tx.status == "FAILED"

    def test_handle_webhook_missing_reference(self, test_user):
        service = PaymentService()
        result = service.handle_webhook({"event_type": "payment.success", "reference": ""})
        assert result["status"] == "error"

    @patch("payments.services.KorapayGateway")
    def test_create_withdrawal(self, mock_cls, test_user, korapay_gateway, verified_kyc):
        test_user.balance = Decimal("100000")
        test_user.save()

        service = PaymentService()
        tx = service.create_withdrawal(
            user=test_user,
            amount=Decimal("10000"),
            currency="NGN",
        )
        assert tx.transaction_type == "WITHDRAWAL"
        assert tx.amount == Decimal("10000")
        assert tx.status == "PENDING"
        expected_fee = Decimal("10000") * (Decimal("2.0") / Decimal("100"))
        assert tx.fee == expected_fee
        assert tx.net_amount == Decimal("10000") - expected_fee

        test_user.refresh_from_db()
        assert test_user.balance == Decimal("90000")

    def test_create_withdrawal_no_kyc(self, test_user, korapay_gateway):
        test_user.balance = Decimal("100000")
        test_user.save()
        service = PaymentService()
        with pytest.raises(ValueError, match="KYC verification"):
            service.create_withdrawal(user=test_user, amount=Decimal("10000"), currency="NGN")

    def test_create_withdrawal_insufficient_balance(self, test_user, korapay_gateway, verified_kyc):
        test_user.balance = Decimal("500")
        test_user.save()
        service = PaymentService()
        with pytest.raises(ValueError, match="Insufficient balance"):
            service.create_withdrawal(user=test_user, amount=Decimal("10000"), currency="NGN")


@pytest.mark.django_db
class TestPaymentAPI:
    def test_get_gateways(self, api_client, korapay_gateway):
        response = api_client.get("/api/v1/payments/gateways/")
        assert response.status_code == 200

    def test_get_transactions(self, auth_client):
        response = auth_client.get("/api/v1/payments/transactions/")
        assert response.status_code == 200

    def test_get_kyc_status(self, auth_client):
        response = auth_client.get("/api/v1/payments/kyc/status/")
        assert response.status_code == 200

    def test_unauthorized_transactions(self, api_client):
        response = api_client.get("/api/v1/payments/transactions/")
        assert response.status_code == 401

    @patch("payments.services.KorapayGateway")
    def test_initialize_deposit(self, mock_cls, auth_client, test_user, korapay_gateway):
        mock_instance = MagicMock()
        mock_instance.initialize_transaction.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.korapay.com/test",
                "access_code": "test_code",
            },
        }
        mock_cls.return_value = mock_instance

        response = auth_client.post("/api/v1/payments/deposit/", {
            "amount": "5000",
            "currency": "NGN",
            "gateway": str(korapay_gateway.id),
        })
        assert response.status_code == 201
        assert "checkout_url" in response.data
        assert "reference" in response.data

    def test_initialize_deposit_invalid_amount(self, auth_client, korapay_gateway):
        response = auth_client.post("/api/v1/payments/deposit/", {
            "amount": "50",
            "currency": "NGN",
        })
        assert response.status_code == 400

    @patch("payments.services.KorapayGateway")
    def test_verify_deposit(self, mock_cls, auth_client, test_user, korapay_gateway):
        tx = Transaction.objects.create(
            user=test_user,
            transaction_type="DEPOSIT",
            amount=Decimal("5000"),
            currency="NGN",
            gateway=korapay_gateway,
            korapay_ref="DK-API-VERIFY",
            fee=Decimal("75"),
            net_amount=Decimal("4925"),
            status="PROCESSING",
        )
        mock_instance = MagicMock()
        mock_instance.verify_transaction.return_value = {
            "status": True,
            "data": {"status": "success"},
        }
        mock_cls.return_value = mock_instance

        response = auth_client.post("/api/v1/payments/verify/", {
            "reference": "DK-API-VERIFY",
        })
        assert response.status_code == 200
        assert response.data["status"] == "COMPLETED"

    def test_verify_deposit_missing_reference(self, auth_client):
        response = auth_client.post("/api/v1/payments/verify/", {})
        assert response.status_code == 400

    def test_korapay_webhook(self, api_client, test_user, korapay_gateway):
        tx = Transaction.objects.create(
            user=test_user,
            transaction_type="DEPOSIT",
            amount=Decimal("5000"),
            currency="NGN",
            gateway=korapay_gateway,
            korapay_ref="DK-WEBHOOK-API",
            fee=Decimal("75"),
            net_amount=Decimal("4925"),
            status="PROCESSING",
        )

        response = api_client.post("/api/v1/payments/webhook/korapay/", {
            "event": "payment.success",
            "data": {
                "reference": "DK-WEBHOOK-API",
                "status": "success",
                "amount": 5000,
                "currency": "NGN",
                "channel": "card",
            },
        }, format="json")
        assert response.status_code == 200

        tx.refresh_from_db()
        assert tx.status == "COMPLETED"

    def test_korapay_webhook_invalid_signature(self, api_client, test_user, korapay_gateway):
        import os
        os.environ["KORA_WEBHOOK_SECRET"] = "test_webhook_secret"

        body = json.dumps({
            "event": "payment.success",
            "data": {"reference": "DK-WEBHOOK-SIG", "status": "success"},
        }).encode()
        signature = hmac.new(b"wrong_secret", body, hashlib.sha256).hexdigest()

        response = api_client.post(
            "/api/v1/payments/webhook/korapay/",
            data=body,
            content_type="application/json",
            HTTP_X_KORAPAY_SIGNATURE=signature,
        )
        assert response.status_code == 401

        os.environ.pop("KORA_WEBHOOK_SECRET", None)

    def test_create_withdrawal(self, auth_client, test_user, korapay_gateway, verified_kyc):
        test_user.balance = Decimal("100000")
        test_user.save()

        response = auth_client.post("/api/v1/payments/withdraw/", {
            "amount": "10000",
            "currency": "NGN",
        })
        assert response.status_code == 201

    def test_create_withdrawal_no_kyc(self, auth_client, test_user, korapay_gateway):
        test_user.balance = Decimal("100000")
        test_user.save()

        response = auth_client.post("/api/v1/payments/withdraw/", {
            "amount": "10000",
            "currency": "NGN",
        })
        assert response.status_code == 400

    def test_kyc_submit(self, auth_client):
        response = auth_client.post("/api/v1/payments/kyc/submit/", {
            "level": "BASIC",
            "document_type": "NIN",
            "document_number": "12345678901",
        })
        assert response.status_code == 201
        assert response.data["status"] == "PENDING"

    def test_payment_methods_list(self, auth_client):
        response = auth_client.get("/api/v1/payments/methods/")
        assert response.status_code == 200

    def test_reconcile_admin_only(self, auth_client):
        response = auth_client.post("/api/v1/payments/reconcile/", {"days": 7})
        assert response.status_code == 403

    def test_reconcile_admin(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post("/api/v1/payments/reconcile/", {"days": 7}, format="json")
        assert response.status_code == 200
        assert "reconciled" in response.data
