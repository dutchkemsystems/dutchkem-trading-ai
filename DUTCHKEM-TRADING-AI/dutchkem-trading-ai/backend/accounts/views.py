from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
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


class SessionListView(generics.ListAPIView):
    serializer_class = UserSerializer

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
