import django.db.models.deletion
import referrals.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Referral",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(default=referrals.models.generate_referral_code, max_length=8, unique=True)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("REGISTERED", "Registered"), ("FIRST_DEPOSIT", "First Deposit"), ("REWARD_PAID", "Reward Paid")], default="PENDING", max_length=20)),
                ("reward_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("referred", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="referrals_received", to=settings.AUTH_USER_MODEL)),
                ("referrer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="referrals_made", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ReferralReward",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("reward_type", models.CharField(choices=[("SIGNUP", "Signup Bonus"), ("FIRST_DEPOSIT", "First Deposit Bonus"), ("TRADING", "Trading Commission")], max_length=20)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PAID", "Paid")], default="PENDING", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("referral", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rewards", to="referrals.referral")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
