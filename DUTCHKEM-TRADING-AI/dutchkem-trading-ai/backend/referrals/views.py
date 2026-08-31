from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Referral, ReferralReward
from .serializers import ReferralSerializer, ReferralRewardSerializer


class ReferralListView(generics.ListAPIView):
    serializer_class = ReferralSerializer

    def get_queryset(self):
        return Referral.objects.filter(referrer=self.request.user)


class CreateReferralView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        referral, created = Referral.objects.get_or_create(
            referrer=request.user,
            defaults={"referrer": request.user}
        )
        return Response({
            "code": referral.code,
            "share_link": f"https://dutchkem.com/register?ref={referral.code}",
            "created": created,
        })


class ApplyReferralView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response(
                {"error": "referral code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            referral = Referral.objects.get(code=code, status="PENDING")
        except Referral.DoesNotExist:
            return Response(
                {"error": "Invalid or already used referral code"},
                status=status.HTTP_400_BAD_REQUEST
            )

        referral.referred = request.user
        referral.status = "REGISTERED"
        referral.save(update_fields=["referred", "status"])

        ReferralReward.objects.create(
            referral=referral,
            amount=10.00,
            reward_type="SIGNUP",
        )

        return Response({"status": "Referral applied successfully"})


class ReferralStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        referrals = Referral.objects.filter(referrer=request.user)
        total_referrals = referrals.count()
        completed = referrals.filter(status__in=["REGISTERED", "FIRST_DEPOSIT", "REWARD_PAID"]).count()
        total_earned = sum(float(r.reward_amount) for r in referrals)

        return Response({
            "total_referrals": total_referrals,
            "completed_referrals": completed,
            "total_earned": total_earned,
            "referral_code": referrals.first().code if referrals.exists() else None,
        })
