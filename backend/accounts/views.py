from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import LoginHistory, UserSession
from .serializers import (
    CustomTokenObtainPairSerializer,
    MFASerializer,
    MFASetupSerializer,
    PasswordChangeSerializer,
    ProfileUpdateSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        # Create session
        UserSession.objects.create(
            user=user, ip_address=request.META.get("REMOTE_ADDR"), user_agent=request.META.get("HTTP_USER_AGENT", "")
        )

        # Log login
        LoginHistory.objects.create(
            user=user,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            status="SUCCESS",
        )

        # Get tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {"refresh": str(refresh), "access": str(refresh.access_token), "user": UserSerializer(user).data}
        )


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()

            # Deactivate sessions
            UserSession.objects.filter(user=request.user, is_active=True).update(is_active=False)

            return Response({"message": "Successfully logged out"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProfileUpdateView(generics.UpdateAPIView):
    serializer_class = ProfileUpdateSerializer

    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response({"message": "Password changed successfully"})


class MFASetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = MFASetupSerializer(data={}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.create({})
        return Response(result)

    def post(self, request):
        serializer = MFASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        device = user.totpdevice_set.filter(confirmed=False).first()

        if device and device.verify_token(serializer.validated_data["code"]):
            device.confirmed = True
            device.save()
            user.mfa_enabled = True
            user.mfa_secret = device.key
            user.save()
            return Response({"message": "MFA enabled successfully"})

        return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)


class MFADisableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MFASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        device = user.totpdevice_set.filter(confirmed=True).first()

        if device and device.verify_token(serializer.validated_data["code"]):
            device.delete()
            user.mfa_enabled = False
            user.mfa_secret = None
            user.save()
            return Response({"message": "MFA disabled successfully"})

        return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)


class MFAEnrollView(APIView):
    """Generate TOTP secret for MFA enrollment"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        import pyotp
        import qrcode
        import io
        import base64

        user = request.user
        secret = pyotp.random_base32()

        user.mfa_secret = secret
        user.save(update_fields=["mfa_secret"])

        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Dutchkem Trading AI"
        )

        return Response({
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "message": "Scan QR code with authenticator app, then verify with /mfa/verify/"
        })


class MFAVerifyView(APIView):
    """Verify TOTP code and enable MFA"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        import pyotp

        user = request.user
        code = request.data.get("code")

        if not code:
            return Response(
                {"error": "code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.mfa_secret:
            return Response(
                {"error": "MFA not enrolled. Call /mfa/enroll/ first"},
                status=status.HTTP_400_BAD_REQUEST
            )

        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(code):
            user.mfa_enabled = True
            user.save(update_fields=["mfa_enabled"])
            return Response({"status": "MFA enabled successfully"})
        else:
            return Response(
                {"error": "Invalid code"},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ["id", "ip_address", "user_agent", "created_at"]


class SessionListView(generics.ListAPIView):
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)


class SessionDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, session_id):
        UserSession.objects.filter(id=session_id, user=request.user).update(is_active=False)
        return Response({"message": "Session terminated"})


class MT5ConnectionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        mt5_account = request.data.get("mt5_account")
        mt5_server = request.data.get("mt5_server")

        user = request.user
        user.mt5_account = mt5_account
        user.mt5_server = mt5_server
        user.save()

        return Response({"message": "MT5 connection details saved"})

    def get(self, request):
        user = request.user
        return Response(
            {
                "mt5_account": user.mt5_account,
                "mt5_server": user.mt5_server,
                "connected": bool(user.mt5_account and user.mt5_server),
            }
        )


# ── Multi-Account Management (V6.5) ────────────────────────────────


class TradingAccountListView(APIView):
    """List all trading accounts for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import TradingAccount
        accounts = TradingAccount.objects.filter(user=request.user).order_by("-is_primary", "account_type")
        data = []
        for a in accounts:
            data.append({
                "id": str(a.id),
                "mt5_login": a.mt5_login,
                "mt5_server": a.mt5_server,
                "mt5_name": a.mt5_name,
                "account_type": a.account_type,
                "status": a.status,
                "is_primary": a.is_primary,
                "balance": float(a.balance),
                "equity": float(a.equity),
                "max_lots": a.get_lots_for_balance(),
                "trading_engine": a.trading_engine,
                "scaling_threshold": float(a.scaling_threshold),
                "created_at": a.created_at.isoformat(),
            })
        return Response({"accounts": data, "count": len(data)})


class TradingAccountCreateView(APIView):
    """Register a new MT5 trading account for multi-account trading."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .models import TradingAccount

        mt5_login = request.data.get("mt5_login")
        mt5_password = request.data.get("mt5_password")
        mt5_server = request.data.get("mt5_server")
        account_type = request.data.get("account_type", "STANDARD")
        is_primary = request.data.get("is_primary", False)

        if not mt5_login or not mt5_password or not mt5_server:
            return Response(
                {"error": "mt5_login, mt5_password, and mt5_server are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = TradingAccount.objects.filter(mt5_login=mt5_login, mt5_server=mt5_server).exists()
        if existing:
            return Response(
                {"error": f"Account {mt5_login}@{mt5_server} is already registered"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = TradingAccount.objects.create(
            user=request.user,
            mt5_login=mt5_login,
            mt5_password=mt5_password,
            mt5_server=mt5_server,
            account_type=account_type,
            is_primary=is_primary,
            trading_engine="v6.5",
        )

        return Response({
            "created": True,
            "account_id": str(account.id),
            "mt5_login": mt5_login,
            "account_type": account_type,
            "is_primary": is_primary,
            "trading_engine": "v6.5",
        }, status=status.HTTP_201_CREATED)


class TradingAccountPortfolioView(APIView):
    """Get portfolio summary across all accounts."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .multi_account_manager import MultiAccountManager
        mgr = MultiAccountManager()
        summary = mgr.get_portfolio_summary(request.user.id)
        return Response(summary)


class TradingAccountScaleView(APIView):
    """Trigger manual scaling check (auto-scaling runs every V6.5 cycle too)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .multi_account_manager import MultiAccountManager
        mgr = MultiAccountManager()
        result = mgr.check_and_scale(request.user.id)
        return Response(result)
