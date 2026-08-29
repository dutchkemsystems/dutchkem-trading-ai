from rest_framework import serializers
from .models import Referral, ReferralReward


class ReferralSerializer(serializers.ModelSerializer):
    referred_username = serializers.CharField(source="referred.username", read_only=True, default=None)

    class Meta:
        model = Referral
        fields = ["id", "code", "status", "referred_username", "reward_amount", "created_at", "completed_at"]
        read_only_fields = ["id", "code", "status", "reward_amount", "created_at", "completed_at"]


class ReferralRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralReward
        fields = "__all__"
