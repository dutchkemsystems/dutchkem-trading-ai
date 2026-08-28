import logging
import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .gateways.korapay import KorapayGateway
from .models import KYCVerification, PaymentGateway, Transaction

logger = logging.getLogger("payments")

SUPPORTED_CURRENCIES = ["NGN", "GHS", "KES", "ZAR"]
SUPPORTED_CHANNELS = ["card", "bank_transfer", "ussd", "mobile_money"]


class PaymentService:
    def __init__(self):
        self.korapay = KorapayGateway()

    @transaction.atomic
    def create_deposit(
        self,
        user,
        amount: Decimal,
        currency: str = "NGN",
        gateway_id: str | None = None,
        channel: str = "",
        redirect_url: str = "",
    ) -> Transaction:
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {currency}. Use one of {SUPPORTED_CURRENCIES}")

        gateway = None
        if gateway_id:
            gateway = PaymentGateway.objects.filter(id=gateway_id, is_active=True).first()

        if not gateway:
            gateway = PaymentGateway.objects.filter(name="KORAPAY", is_active=True).first()

        if not gateway:
            raise ValueError("No active payment gateway found")

        if amount < gateway.min_deposit:
            raise ValueError(f"Minimum deposit is {gateway.min_deposit}")
        if gateway.max_deposit and amount > gateway.max_deposit:
            raise ValueError(f"Maximum deposit is {gateway.max_deposit}")

        fee = amount * (gateway.deposit_fee_percent / Decimal("100"))
        net_amount = amount - fee
        reference = f"DK-{uuid.uuid4().hex[:12].upper()}"

        tx = Transaction.objects.create(
            user=user,
            transaction_type="DEPOSIT",
            amount=amount,
            currency=currency,
            gateway=gateway,
            gateway_reference=reference,
            korapay_ref=reference,
            channel=channel,
            fee=fee,
            net_amount=net_amount,
            status="PENDING",
            metadata={"initiated_by": "api", "redirect_url": redirect_url},
        )

        korapay_result = self.korapay.initialize_transaction(
            amount=float(amount),
            currency=currency,
            reference=reference,
            customer_email=user.email,
            customer_name=f"{user.first_name} {user.last_name}".strip(),
            description=f"Deposit {amount} {currency}",
            metadata={"transaction_id": str(tx.id), "user_id": str(user.id)},
            redirect_url=redirect_url,
        )

        if korapay_result.get("status") is True or korapay_result.get("status") == "success":
            tx.gateway_response = korapay_result
            tx.status = "PROCESSING"
            tx.save()
        else:
            tx.status = "FAILED"
            tx.gateway_response = korapay_result
            tx.save()
            logger.warning("Korapay init failed for tx %s: %s", tx.id, korapay_result)

        return tx

    @transaction.atomic
    def verify_deposit(self, reference: str) -> Transaction:
        tx = Transaction.objects.select_for_update().filter(
            korapay_ref=reference, transaction_type="DEPOSIT"
        ).first()

        if not tx:
            raise Transaction.DoesNotExist(f"Transaction not found: {reference}")

        if tx.status == "COMPLETED":
            return tx

        result = self.korapay.verify_transaction(reference)
        tx.gateway_response = result

        korapay_status = result.get("data", {}).get("status", result.get("status", ""))
        if korapay_status in ("success", "completed"):
            tx.status = "COMPLETED"
            tx.completed_at = timezone.now()
            tx.channel = result.get("data", {}).get("channel", tx.channel)
            tx.save()

            from accounts.models import User
            User.objects.filter(id=tx.user_id).update(
                balance=F("balance") + tx.net_amount
            )
            logger.info("Deposit completed: tx=%s amount=%s", tx.id, tx.net_amount)
        elif korapay_status in ("failed", "abandoned"):
            tx.status = "FAILED"
            tx.save()
        else:
            tx.status = "PROCESSING"
            tx.save()

        return tx

    @transaction.atomic
    def create_withdrawal(
        self,
        user,
        amount: Decimal,
        currency: str = "NGN",
        gateway_id: str | None = None,
        channel: str = "",
    ) -> Transaction:
        kyc = KYCVerification.objects.filter(user=user, status="VERIFIED").first()
        if not kyc:
            raise ValueError("KYC verification required for withdrawals")

        gateway = None
        if gateway_id:
            gateway = PaymentGateway.objects.filter(id=gateway_id, is_active=True).first()
        if not gateway:
            gateway = PaymentGateway.objects.filter(name="KORAPAY", is_active=True).first()
        if not gateway:
            raise ValueError("No active payment gateway found")

        if amount < gateway.min_withdrawal:
            raise ValueError(f"Minimum withdrawal is {gateway.min_withdrawal}")
        if gateway.max_withdrawal and amount > gateway.max_withdrawal:
            raise ValueError(f"Maximum withdrawal is {gateway.max_withdrawal}")

        if Decimal(str(user.balance)) < amount:
            raise ValueError("Insufficient balance")

        fee = amount * (gateway.withdrawal_fee_percent / Decimal("100"))
        net_amount = amount - fee
        reference = f"DKW-{uuid.uuid4().hex[:12].upper()}"

        tx = Transaction.objects.create(
            user=user,
            transaction_type="WITHDRAWAL",
            amount=amount,
            currency=currency,
            gateway=gateway,
            gateway_reference=reference,
            korapay_ref=reference,
            channel=channel,
            fee=fee,
            net_amount=net_amount,
            status="PENDING",
        )

        from accounts.models import User
        User.objects.filter(id=user.id).update(balance=F("balance") - amount)

        logger.info("Withdrawal created: tx=%s amount=%s user=%s", tx.id, amount, user.username)
        return tx

    def handle_webhook(self, event_data: dict) -> dict:
        event_type = event_data.get("event_type", "")
        reference = event_data.get("reference", "")

        if not reference:
            return {"status": "error", "message": "Missing reference"}

        tx = Transaction.objects.filter(korapay_ref=reference).first()
        if not tx:
            logger.warning("Webhook for unknown reference: %s", reference)
            return {"status": "error", "message": "Transaction not found"}

        if tx.status == "COMPLETED":
            return {"status": "ok", "transaction_id": str(tx.id), "message": "Already processed"}

        if event_type == "payment.success":
            if tx.status != "COMPLETED":
                tx.status = "COMPLETED"
                tx.completed_at = timezone.now()
                tx.channel = event_data.get("channel", tx.channel)
                tx.gateway_response = event_data
                tx.save()

                if tx.transaction_type == "DEPOSIT":
                    from accounts.models import User
                    User.objects.filter(id=tx.user_id).update(
                        balance=F("balance") + tx.net_amount
                    )
                    logger.info("Webhook deposit completed: tx=%s amount=%s", tx.id, tx.net_amount)
        elif event_type == "payment.failed":
            if tx.status not in ("COMPLETED", "CANCELLED"):
                tx.status = "FAILED"
                tx.gateway_response = event_data
                tx.save()
                logger.info("Webhook payment failed: tx=%s", tx.id)
        elif event_type == "payment.pending":
            tx.status = "PROCESSING"
            tx.gateway_response = event_data
            tx.save()

        return {"status": "ok", "transaction_id": str(tx.id)}

    def reconcile_transactions(self, days: int = 7) -> dict:
        from django.utils import timezone as tz
        from datetime import timedelta

        cutoff = tz.now() - timedelta(days=days)
        pending_txs = Transaction.objects.filter(
            status="PROCESSING",
            created_at__gte=cutoff,
            transaction_type="DEPOSIT",
        )

        reconciled = 0
        failed = 0
        for tx in pending_txs:
            result = self.korapay.verify_transaction(tx.korapay_ref)
            korapay_status = result.get("data", {}).get("status", result.get("status", ""))
            if korapay_status in ("success", "completed"):
                tx.status = "COMPLETED"
                tx.completed_at = tz.now()
                tx.gateway_response = result
                tx.save()
                from accounts.models import User
                User.objects.filter(id=tx.user_id).update(
                    balance=F("balance") + tx.net_amount
                )
                reconciled += 1
            elif korapay_status in ("failed", "abandoned"):
                tx.status = "FAILED"
                tx.gateway_response = result
                tx.save()
                failed += 1

        return {"reconciled": reconciled, "failed": failed, "total_pending": pending_txs.count()}
