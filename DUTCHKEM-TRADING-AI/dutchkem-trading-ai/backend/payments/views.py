import hashlib
import hmac
import json
import logging
import os

from django.db import models
from django.db.models import F
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KYCVerification, PaymentGateway, Transaction, UserPaymentMethod
from .serializers import (
    DepositSerializer,
    KYCVerificationSerializer,
    PaymentGatewaySerializer,
    TransactionSerializer,
    UserPaymentMethodSerializer,
    WithdrawalSerializer,
)
from .services import PaymentService

logger = logging.getLogger("payments")


class PaymentGatewayListView(generics.ListAPIView):
    queryset = PaymentGateway.objects.filter(is_active=True)
    serializer_class = PaymentGatewaySerializer
    permission_classes = [permissions.AllowAny]


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        tx_type = self.request.query_params.get("type")
        if tx_type:
            queryset = queryset.filter(transaction_type=tx_type)
        tx_status = self.request.query_params.get("status")
        if tx_status:
            queryset = queryset.filter(status=tx_status)
        return queryset


class TransactionDetailView(generics.RetrieveAPIView):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class InitializeDepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PaymentService()
        try:
            redirect_url = serializer.validated_data.get("redirect_url", "")
            if not redirect_url:
                frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
                redirect_url = f"{frontend_url}/payments/callback"

            tx = service.create_deposit(
                user=request.user,
                amount=serializer.validated_data["amount"],
                currency=serializer.validated_data.get("currency", "NGN"),
                gateway_id=serializer.validated_data.get("gateway"),
                channel=serializer.validated_data.get("channel", ""),
                redirect_url=redirect_url,
            )

            checkout_url = ""
            access_code = ""
            if tx.gateway_response:
                data_section = tx.gateway_response.get("data", {})
                checkout_url = data_section.get("authorization_url", data_section.get("checkout_url", ""))
                access_code = data_section.get("access_code", "")

            return Response(
                {
                    "transaction_id": str(tx.id),
                    "reference": tx.korapay_ref,
                    "amount": str(tx.amount),
                    "currency": tx.currency,
                    "status": tx.status,
                    "checkout_url": checkout_url,
                    "access_code": access_code,
                    "fee": str(tx.fee),
                    "net_amount": str(tx.net_amount),
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyDepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reference = request.data.get("reference")
        if not reference:
            return Response({"error": "Reference is required"}, status=status.HTTP_400_BAD_REQUEST)

        service = PaymentService()
        try:
            tx = service.verify_deposit(reference)
            return Response(
                {
                    "transaction_id": str(tx.id),
                    "reference": tx.korapay_ref,
                    "status": tx.status,
                    "amount": str(tx.amount),
                    "currency": tx.currency,
                    "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
                }
            )
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)


class CreateWithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PaymentService()
        try:
            tx = service.create_withdrawal(
                user=request.user,
                amount=serializer.validated_data["amount"],
                currency=serializer.validated_data.get("currency", "NGN"),
                gateway_id=serializer.validated_data.get("gateway"),
                channel=serializer.validated_data.get("channel", ""),
            )
            return Response(
                {
                    "transaction_id": str(tx.id),
                    "reference": tx.korapay_ref,
                    "amount": str(tx.amount),
                    "currency": tx.currency,
                    "status": tx.status,
                    "fee": str(tx.fee),
                    "net_amount": str(tx.net_amount),
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithdrawalStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, transaction_id):
        try:
            tx = Transaction.objects.get(
                id=transaction_id,
                user=request.user,
                transaction_type="WITHDRAWAL",
            )
            return Response(
                {
                    "transaction_id": str(tx.id),
                    "reference": tx.korapay_ref,
                    "status": tx.status,
                    "amount": str(tx.amount),
                    "currency": tx.currency,
                    "fee": str(tx.fee),
                    "net_amount": str(tx.net_amount),
                    "created_at": tx.created_at.isoformat(),
                    "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
                }
            )
        except Transaction.DoesNotExist:
            return Response(
                {"error": "Transaction not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class UserBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        total_deposits = Transaction.objects.filter(
            user=user, transaction_type="DEPOSIT", status="COMPLETED"
        ).aggregate(total=models.Sum("net_amount"))["total"] or 0

        total_withdrawals = Transaction.objects.filter(
            user=user, transaction_type="WITHDRAWAL", status="COMPLETED"
        ).aggregate(total=models.Sum("amount"))["total"] or 0

        return Response(
            {
                "balance": str(user.balance),
                "equity": str(user.equity),
                "total_deposits": str(total_deposits),
                "total_withdrawals": str(total_withdrawals),
                "currency": user.preferred_currency,
            }
        )


class KorapayWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get("x-korapay-signature", "")
        raw_body = request.body

        webhook_secret = os.environ.get("KORA_WEBHOOK_SECRET", "")
        if not webhook_secret:
            logger.warning("KORA_WEBHOOK_SECRET not set, rejecting webhook")
            return Response({"error": "Webhook secret not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        expected = hmac.HMAC(
            webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logger.warning("Invalid Korapay webhook signature")
            return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        body = request.data
        event_data = {
            "event_type": body.get("event", ""),
            "reference": body.get("data", {}).get("reference", ""),
            "status": body.get("data", {}).get("status", ""),
            "amount": body.get("data", {}).get("amount", 0),
            "currency": body.get("data", {}).get("currency", ""),
            "channel": body.get("data", {}).get("channel", ""),
            "metadata": body.get("data", {}).get("metadata", {}),
            "paid_at": body.get("data", {}).get("paid_at"),
        }

        service = PaymentService()
        result = service.handle_webhook(event_data)
        return Response(result)


class PaymentCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        reference = request.query_params.get("reference", "")
        trxref = request.query_params.get("trxref", "")
        ref = reference or trxref

        if not ref:
            return Response({"error": "No reference provided"}, status=status.HTTP_400_BAD_REQUEST)

        service = PaymentService()
        try:
            tx = service.verify_deposit(ref)
            frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
            from django.shortcuts import redirect
            return redirect(f"{frontend_url}/payments?status={tx.status}&reference={ref}")
        except Transaction.DoesNotExist:
            frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
            from django.shortcuts import redirect
            return redirect(f"{frontend_url}/payments?status=FAILED&reference={ref}")


class ReconcileView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        days = request.data.get("days", 7)
        service = PaymentService()
        result = service.reconcile_transactions(days=days)
        return Response(result)


class KYCSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = KYCVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kyc = serializer.save(user=request.user, status="PENDING", submitted_at=timezone.now())
        return Response(KYCVerificationSerializer(kyc).data, status=status.HTTP_201_CREATED)


class KYCStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        kyc = KYCVerification.objects.filter(user=request.user).first()
        if kyc:
            return Response(KYCVerificationSerializer(kyc).data)
        return Response({"status": "NOT_STARTED"})


class PaymentMethodListView(generics.ListAPIView):
    serializer_class = UserPaymentMethodSerializer

    def get_queryset(self):
        return UserPaymentMethod.objects.filter(user=self.request.user)


class PaymentMethodCreateView(generics.CreateAPIView):
    serializer_class = UserPaymentMethodSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
