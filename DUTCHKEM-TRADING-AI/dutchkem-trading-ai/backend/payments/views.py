from django.utils import timezone
from rest_framework import generics, permissions
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
        return queryset


class DepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gateway = PaymentGateway.objects.get(id=serializer.validated_data["gateway"])
        amount = serializer.validated_data["amount"]

        # Validate limits
        if amount < gateway.min_deposit:
            return Response({"error": f"Minimum deposit is {gateway.min_deposit}"}, status=400)
        if gateway.max_deposit and amount > gateway.max_deposit:
            return Response({"error": f"Maximum deposit is {gateway.max_deposit}"}, status=400)

        fee = amount * (gateway.deposit_fee_percent / 100)
        net_amount = amount - fee

        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type="DEPOSIT",
            amount=amount,
            gateway=gateway,
            fee=fee,
            net_amount=net_amount,
            status="PENDING",
        )

        return Response(TransactionSerializer(transaction).data, status=201)


class WithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gateway = PaymentGateway.objects.get(id=serializer.validated_data["gateway"])
        amount = serializer.validated_data["amount"]

        # Check KYC
        kyc = KYCVerification.objects.filter(user=request.user, status="VERIFIED").first()
        if not kyc:
            return Response({"error": "KYC verification required for withdrawals"}, status=400)

        # Check balance
        if amount > request.user.balance:
            return Response({"error": "Insufficient balance"}, status=400)

        # Validate limits
        if amount < gateway.min_withdrawal:
            return Response({"error": f"Minimum withdrawal is {gateway.min_withdrawal}"}, status=400)

        fee = amount * (gateway.withdrawal_fee_percent / 100)
        net_amount = amount - fee

        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type="WITHDRAWAL",
            amount=amount,
            gateway=gateway,
            fee=fee,
            net_amount=net_amount,
            status="PENDING",
        )

        return Response(TransactionSerializer(transaction).data, status=201)


class KYCSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = KYCVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kyc = serializer.save(user=request.user, status="PENDING", submitted_at=timezone.now())

        return Response(KYCVerificationSerializer(kyc).data, status=201)


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


class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
