import uuid
import string
import random
from django.conf import settings
from django.db import models


def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class Referral(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals_made"
    )
    referred = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals_received",
        null=True, blank=True
    )
    code = models.CharField(max_length=8, unique=True, default=generate_referral_code)
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("REGISTERED", "Registered"),
            ("FIRST_DEPOSIT", "First Deposit"),
            ("REWARD_PAID", "Reward Paid"),
        ],
        default="PENDING"
    )
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.referrer.username} → {self.code}"


class ReferralReward(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="rewards")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reward_type = models.CharField(
        max_length=20,
        choices=[
            ("SIGNUP", "Signup Bonus"),
            ("FIRST_DEPOSIT", "First Deposit Bonus"),
            ("TRADING", "Trading Commission"),
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("PAID", "Paid")],
        default="PENDING"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reward_type} - ${self.amount}"
