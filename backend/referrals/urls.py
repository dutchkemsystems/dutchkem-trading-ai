from django.urls import path
from . import views

urlpatterns = [
    path("", views.ReferralListView.as_view(), name="referral_list"),
    path("create/", views.CreateReferralView.as_view(), name="create_referral"),
    path("apply/", views.ApplyReferralView.as_view(), name="apply_referral"),
    path("stats/", views.ReferralStatsView.as_view(), name="referral_stats"),
]
