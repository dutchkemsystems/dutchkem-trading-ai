from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Dutchkem Trading AI API",
        default_version="v1",
        description="""
# Dutchkem Trading AI — API Documentation

## Overview
Comprehensive forex trading platform with multi-timeframe analysis, AI signal generation, 
and risk management. Supports 6 timeframes (M5, M15, M30, H1, H2, H4) with daily-focused 
risk parameters (0.14% daily growth, 2% max daily loss).

## Authentication
All endpoints require JWT authentication unless noted otherwise.
- **Login**: `POST /api/v1/auth/login/` — Returns access and refresh tokens
- **Register**: `POST /api/v1/auth/register/` — Create new account
- **Token Refresh**: `POST /api/v1/auth/refresh/` — Refresh expired access token

## Core Modules
- **Trading**: Symbols, trades, orders, positions, portfolio
- **Indicators**: 100+ technical indicators, timeframes, categories
- **Signals**: AI-generated trading signals with confluence scoring
- **Risk Management**: Daily risk limits, drawdown monitoring, circuit breakers
- **Payments**: Multi-gateway deposits/withdrawals, KYC verification
- **Expert Advisors**: EA management, MQL5 code generation
- **Market Data**: Real-time prices, economic calendar, sentiment
- **MCP Integration**: SYNX-MT5, AkTools, OpenAlgo, CrossTrade, OpenTrading

## Rate Limits
- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
        """,
        terms_of_service="https://www.dutchkem.com/terms/",
        contact=openapi.Contact(
            name="Dutchkem Trading AI Support", email="api@dutchkem.com", url="https://www.dutchkem.com/support"
        ),
        license=openapi.License(name="Proprietary", url="https://www.dutchkem.com/license"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    patterns=[
        path("api/v1/", include("accounts.urls")),
        path("api/v1/trading/", include("trading.urls")),
        path("api/v1/indicators/", include("indicators.urls")),
        path("api/v1/signals/", include("signals.urls")),
        path("api/v1/risk/", include("risk_management.urls")),
        path("api/v1/payments/", include("payments.urls")),
        path("api/v1/eas/", include("expert_advisors.urls")),
        path("api/v1/market/", include("market_data.urls")),
        path("api/v1/notifications/", include("notifications.urls")),
    ],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/trading/", include("trading.urls")),
    path("api/v1/indicators/", include("indicators.urls")),
    path("api/v1/signals/", include("signals.urls")),
    path("api/v1/risk/", include("risk_management.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/eas/", include("expert_advisors.urls")),
    path("api/v1/market/", include("market_data.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/analytics/", include("analytics.urls")),
    path("api/v1/mcp/", include("mcp_integration.urls")),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
