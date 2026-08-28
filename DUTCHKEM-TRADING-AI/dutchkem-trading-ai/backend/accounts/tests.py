import pytest
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            username="trader1",
            email="trader1@test.com",
            password="TestPass123!",
        )
        assert user.username == "trader1"
        assert user.email == "trader1@test.com"
        assert user.role == "TRADER"
        assert user.check_password("TestPass123!")
        assert not user.is_staff

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin1",
            email="admin1@test.com",
            password="AdminPass123!",
        )
        assert admin.is_staff
        assert admin.is_superuser

    def test_user_str(self):
        user = User.objects.create_user(
            username="trader2",
            email="trader2@test.com",
            password="TestPass123!",
        )
        assert str(user) == "trader2 (trader2@test.com)"

    def test_lock_account(self):
        user = User.objects.create_user(
            username="trader3",
            email="trader3@test.com",
            password="TestPass123!",
        )
        user.lock_account(duration_minutes=30)
        user.refresh_from_db()
        assert user.account_locked_until is not None
        assert user.is_account_locked()

    def test_is_not_locked_by_default(self):
        user = User.objects.create_user(
            username="trader4",
            email="trader4@test.com",
            password="TestPass123!",
        )
        assert not user.is_account_locked()

    def test_default_balance(self):
        user = User.objects.create_user(
            username="trader5",
            email="trader5@test.com",
            password="TestPass123!",
        )
        assert user.balance == Decimal("0")
        assert user.equity == Decimal("0")

    def test_kyc_status_default(self):
        user = User.objects.create_user(
            username="trader6",
            email="trader6@test.com",
            password="TestPass123!",
        )
        assert user.kyc_status == "NOT_STARTED"

    def test_user_roles(self):
        for role in ["TRADER", "ADMIN", "VIEWER"]:
            user = User.objects.create_user(
                username=f"role_{role.lower()}",
                email=f"{role.lower()}@test.com",
                password="TestPass123!",
                role=role,
            )
            assert user.role == role

    def test_account_lock_expiry(self):
        user = User.objects.create_user(
            username="trader_lock",
            email="lock@test.com",
            password="TestPass123!",
        )
        user.lock_account(duration_minutes=-1)
        user.refresh_from_db()
        assert not user.is_account_locked()


@pytest.mark.django_db
class TestAuthAPI:
    def test_register(self, api_client):
        response = api_client.post("/api/v1/auth/register/", {
            "username": "newtrader",
            "email": "new@test.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "first_name": "New",
            "last_name": "Trader",
        })
        assert response.status_code == 201
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]

    def test_register_password_mismatch(self, api_client):
        response = api_client.post("/api/v1/auth/register/", {
            "username": "traderx",
            "email": "x@test.com",
            "password": "Pass123!",
            "password_confirm": "DifferentPass123!",
        })
        assert response.status_code == 400

    def test_register_duplicate_username(self, api_client, test_user):
        response = api_client.post("/api/v1/auth/register/", {
            "username": "testtrader",
            "email": "another@test.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        assert response.status_code == 400

    def test_login(self, api_client, test_user):
        response = api_client.post("/api/v1/auth/login/", {
            "username": "testtrader",
            "password": "TestPass123!",
        })
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data

    def test_login_invalid_credentials(self, api_client, test_user):
        response = api_client.post("/api/v1/auth/login/", {
            "username": "testtrader",
            "password": "WrongPassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post("/api/v1/auth/login/", {
            "username": "nonexistent",
            "password": "TestPass123!",
        })
        assert response.status_code == 401

    def test_profile(self, auth_client, test_user):
        response = auth_client.get("/api/v1/profile/")
        assert response.status_code == 200
        assert response.data["username"] == "testtrader"

    def test_profile_update(self, auth_client, test_user):
        response = auth_client.put("/api/v1/profile/update/", {
            "first_name": "Updated",
            "last_name": "Name",
            "phone_number": "+1234567890",
        })
        assert response.status_code == 200

    def test_password_change(self, auth_client, test_user):
        response = auth_client.post("/api/v1/auth/password-change/", {
            "old_password": "TestPass123!",
            "new_password": "NewStrongPass456!",
        })
        assert response.status_code == 200
        test_user.refresh_from_db()
        assert test_user.check_password("NewStrongPass456!")

    def test_password_change_wrong_old(self, auth_client, test_user):
        response = auth_client.post("/api/v1/auth/password-change/", {
            "old_password": "WrongPass!",
            "new_password": "NewStrongPass456!",
        })
        assert response.status_code == 400

    def test_unauthorized_profile(self, api_client):
        response = api_client.get("/api/v1/profile/")
        assert response.status_code == 401

    def test_logout(self, auth_client, test_user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(test_user)
        response = auth_client.post("/api/v1/auth/logout/", {
            "refresh": str(refresh),
        })
        assert response.status_code in (200, 204, 205)

    def test_token_refresh(self, api_client, test_user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(test_user)
        response = api_client.post("/api/v1/auth/refresh/", {
            "refresh": str(refresh),
        })
        assert response.status_code == 200
        assert "access" in response.data

    def test_mfa_setup(self, auth_client):
        response = auth_client.get("/api/v1/auth/mfa/setup/")
        assert response.status_code in (200, 404)

    def test_sessions(self, auth_client):
        response = auth_client.get("/api/v1/sessions/")
        assert response.status_code == 200
