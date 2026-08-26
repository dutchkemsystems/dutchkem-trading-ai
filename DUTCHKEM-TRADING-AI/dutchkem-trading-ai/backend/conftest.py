# Dutchkem Trading AI — Test Configuration

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="testtrader",
        email="trader@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Trader",
        role="TRADER",
    )


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin", email="admin@test.com", password="adminpass123", first_name="Admin", last_name="User"
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client
