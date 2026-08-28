from django.urls import path

from . import views

urlpatterns = [
    path("gateways/", views.PaymentGatewayListView.as_view(), name="payment_gateway_list"),
    path("transactions/", views.TransactionListView.as_view(), name="transaction_list"),
    path("transactions/<uuid:pk>/", views.TransactionDetailView.as_view(), name="transaction_detail"),
    path("deposit/", views.InitializeDepositView.as_view(), name="initialize_deposit"),
    path("verify/", views.VerifyDepositView.as_view(), name="verify_deposit"),
    path("withdraw/", views.CreateWithdrawalView.as_view(), name="create_withdrawal"),
    path("webhook/korapay/", views.KorapayWebhookView.as_view(), name="korapay_webhook"),
    path("callback/", views.PaymentCallbackView.as_view(), name="payment_callback"),
    path("reconcile/", views.ReconcileView.as_view(), name="payment_reconcile"),
    path("kyc/submit/", views.KYCSubmitView.as_view(), name="kyc_submit"),
    path("kyc/status/", views.KYCStatusView.as_view(), name="kyc_status"),
    path("methods/", views.PaymentMethodListView.as_view(), name="payment_method_list"),
    path("methods/create/", views.PaymentMethodCreateView.as_view(), name="payment_method_create"),
]
