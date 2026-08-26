# Dutchkem Trading AI — Payments Tests

from decimal import Decimal

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestPaymentGatewayModel:
    def test_create_gateway(self):
        from payments.models import PaymentGateway

        gateway = PaymentGateway.objects.create(
            name="STRIPE",
            display_name="Stripe",
            is_active=True,
            supports_deposits=True,
            supports_withdrawals=True,
            min_deposit=Decimal("50"),
            deposit_fee_percent=Decimal("0"),
            withdrawal_fee_percent=Decimal("0"),
        )
        assert gateway.name == "STRIPE"
        assert gateway.is_active is True


@pytest.mark.django_db
class TestTransactionModel:
    def test_create_transaction(self, user):
        from payments.models import PaymentGateway, Transaction

        gateway = PaymentGateway.objects.create(name="STRIPE", display_name="Stripe", is_active=True)
        tx = Transaction.objects.create(
            user=user,
            transaction_type="DEPOSIT",
            amount=Decimal("1000"),
            currency="USD",
            status="PENDING",
            gateway=gateway,
            fee=Decimal("0"),
            net_amount=Decimal("1000"),
        )
        assert tx.transaction_type == "DEPOSIT"
        assert tx.amount == Decimal("1000")


@pytest.mark.django_db
class TestPaymentEndpoints:
    def test_get_gateways(self, authenticated_client):
        response = authenticated_client.get("/api/v1/payments/gateways/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_transactions(self, authenticated_client, user):
        response = authenticated_client.get("/api/v1/payments/transactions/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_kyc_status(self, authenticated_client):
        response = authenticated_client.get("/api/v1/payments/kyc/status/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
