from django.contrib import admin
from .models import Referral, ReferralReward


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ["referrer", "code", "status", "reward_amount", "created_at"]
    list_filter = ["status"]
    search_fields = ["referrer__username", "code"]


@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = ["referral", "amount", "reward_type", "status", "created_at"]
    list_filter = ["reward_type", "status"]
