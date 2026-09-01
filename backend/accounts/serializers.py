import base64
import io

import qrcode
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "avatar",
            "country",
            "mfa_enabled",
            "kyc_status",
            "mt5_account",
            "mt5_server",
            "balance",
            "equity",
            "preferred_currency",
            "timezone",
            "notifications_enabled",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "kyc_status", "balance", "equity"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone_number",
            "country",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    mfa_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        mfa_code = attrs.get("mfa_code")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")

        if user.is_account_locked():
            raise serializers.ValidationError("Account is temporarily locked")

        if not user.check_password(password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.lock_account()
            user.save()
            raise serializers.ValidationError("Invalid credentials")

        if user.mfa_enabled and not mfa_code:
            raise serializers.ValidationError("MFA code required")

        if user.mfa_enabled and mfa_code:
            device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
            if not device or not device.verify_token(mfa_code):
                raise serializers.ValidationError("Invalid MFA code")

        user.failed_login_attempts = 0
        user.last_login_ip = self.context.get("request").META.get("REMOTE_ADDR")
        user.save()

        attrs["user"] = user
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class MFASerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

    def validate_code(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("MFA code must be 6 digits")
        return value


class MFASetupSerializer(serializers.Serializer):
    def validate(self, attrs):
        user = self.context["request"].user
        if user.mfa_enabled:
            raise serializers.ValidationError("MFA is already enabled")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        device = TOTPDevice.objects.create(user=user, name=f"{user.username}_authenticator")

        # Generate QR code
        provisioning_uri = device.config_url
        qr = qrcode.make(provisioning_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()

        return {"secret": device.key, "qr_code": qr_code, "provisioning_uri": provisioning_uri}


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "avatar",
            "country",
            "preferred_currency",
            "timezone",
            "notifications_enabled",
        ]
