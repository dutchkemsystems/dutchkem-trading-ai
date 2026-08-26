# Dutchkem Trading AI — Accounts Tests

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="trader", email="trader@test.com", password="pass123")
        assert user.username == "trader"
        assert user.email == "trader@test.com"
        assert user.is_active is True
        assert user.check_password("pass123")

    def test_create_superuser(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_superuser(username="admin", email="admin@test.com", password="admin123")
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_user_str(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="trader", email="trader@test.com", password="pass123")
        assert "trader" in str(user)

    def test_account_not_locked_by_default(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="trader", email="trader@test.com", password="pass123")
        assert user.is_active is True


@pytest.mark.django_db
class TestAuthEndpoints:
    def test_register(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "username": "newtrader",
                "email": "new@test.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "first_name": "New",
                "last_name": "Trader",
            },
        )
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_login(self, api_client, user):
        response = api_client.post("/api/v1/auth/login/", {"username": "testtrader", "password": "testpass123"})
        assert response.status_code == status.HTTP_200_OK

    def test_login_invalid_credentials(self, api_client, user):
        response = api_client.post("/api/v1/auth/login/", {"username": "testtrader", "password": "wrongpass"})
        assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile(self, authenticated_client, user):
        response = authenticated_client.get("/api/v1/profile/")
        assert response.status_code == status.HTTP_200_OK

    def test_update_profile(self, authenticated_client, user):
        response = authenticated_client.patch("/api/v1/profile/update/", {"first_name": "Updated"})
        assert response.status_code == status.HTTP_200_OK

    def test_logout(self, authenticated_client, user):
        login_response = authenticated_client.post(
            "/api/v1/auth/login/", {"username": "testtrader", "password": "testpass123"}
        )
        refresh_token = login_response.data.get("refresh", "")
        response = authenticated_client.post("/api/v1/auth/logout/", {"refresh": refresh_token})
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)
