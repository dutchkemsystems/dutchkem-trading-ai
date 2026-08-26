from django.urls import path

from . import views

urlpatterns = [
    path("gateways/", views.PaymentGatewayListView.as_view(), name="payment_gateway_list"),
    path("transactions/", views.TransactionListView.as_view(), name="transaction_list"),
    path("transactions/<uuid:pk>/", views.TransactionDetailView.as_view(), name="transaction_detail"),
    path("deposit/", views.DepositView.as_view(), name="deposit"),
    path("withdraw/", views.WithdrawalView.as_view(), name="withdrawal"),
    path("kyc/submit/", views.KYCSubmitView.as_view(), name="kyc_submit"),
    path("kyc/status/", views.KYCStatusView.as_view(), name="kyc_status"),
    path("methods/", views.PaymentMethodListView.as_view(), name="payment_method_list"),
    path("methods/create/", views.PaymentMethodCreateView.as_view(), name="payment_method_create"),
]
