from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/login/", views.CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/password-change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("auth/mfa/setup/", views.MFASetupView.as_view(), name="mfa_setup"),
    path("auth/mfa/disable/", views.MFADisableView.as_view(), name="mfa_disable"),
    path("mfa/enroll/", views.MFAEnrollView.as_view(), name="mfa_enroll"),
    path("mfa/verify/", views.MFAVerifyView.as_view(), name="mfa_verify"),
    path("mfa/disable/", views.MFADisableView.as_view(), name="mfa_disable_v2"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/update/", views.ProfileUpdateView.as_view(), name="profile_update"),
    path("sessions/", views.SessionListView.as_view(), name="session_list"),
    path("sessions/<uuid:session_id>/", views.SessionDeleteView.as_view(), name="session_delete"),
    path("mt5/connection/", views.MT5ConnectionView.as_view(), name="mt5_connection"),
]
