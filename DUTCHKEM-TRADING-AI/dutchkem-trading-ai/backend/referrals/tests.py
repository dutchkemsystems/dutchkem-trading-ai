from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from referrals.models import Referral, ReferralReward

User = get_user_model()


class ReferralModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )

    def test_create_referral(self):
        referral = Referral.objects.create(referrer=self.user)
        self.assertIsNotNone(referral.code)
        self.assertEqual(len(referral.code), 8)
        self.assertEqual(referral.status, "PENDING")

    def test_referral_str(self):
        referral = Referral.objects.create(referrer=self.user)
        self.assertIn("testuser", str(referral))

    def test_unique_code(self):
        r1 = Referral.objects.create(referrer=self.user)
        r2 = Referral.objects.create(referrer=self.user)
        self.assertNotEqual(r1.code, r2.code)


class ReferralRewardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.referral = Referral.objects.create(referrer=self.user)

    def test_create_reward(self):
        reward = ReferralReward.objects.create(
            referral=self.referral,
            amount=10.00,
            reward_type="SIGNUP",
        )
        self.assertEqual(float(reward.amount), 10.00)
        self.assertEqual(reward.status, "PENDING")


class ReferralAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@test.com"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_referrals(self):
        response = self.client.get("/api/v1/referrals/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_referral(self):
        response = self.client.post("/api/v1/referrals/create/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("code", response.data)

    def test_referral_stats(self):
        response = self.client.get("/api/v1/referrals/stats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_referrals", response.data)

    def test_apply_referral_invalid_code(self):
        response = self.client.post("/api/v1/referrals/apply/", {"code": "INVALID"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
