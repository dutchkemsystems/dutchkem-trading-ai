from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.urls import include, path


def health_check(request):
    health = {"status": "healthy", "checks": {}}

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health["checks"]["database"] = "connected"
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = f"error: {str(e)}"
        return JsonResponse(health, status=500)

    # Redis check
    try:
        from django.core.cache import cache
        cache.set("health_check", "ok", 10)
        val = cache.get("health_check")
        if val == "ok":
            health["checks"]["redis"] = "connected"
        else:
            health["checks"]["redis"] = "error: value mismatch"
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["redis"] = f"error: {str(e)}"

    # Celery check
    try:
        from config.celery import app as celery_app
        inspect = celery_app.control.inspect(timeout=5.0)
        active_workers = inspect.active() or {}
        health["checks"]["celery_workers"] = f"{len(active_workers)} active"
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["celery_workers"] = f"error: {str(e)}"

    return JsonResponse(health)


from config.monitoring import metrics


def metrics_view(request):
    return HttpResponse(metrics.export_prometheus(), content_type='text/plain')


urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("metrics/", metrics_view, name="metrics"),
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
    path("api/v1/referrals/", include("referrals.urls")),
    path("api/v1/ml/", include("ml.urls")),
    path("api/v1/backtesting/", include("backtesting.urls")),
    path("api/v1/gold-edge/", include("gold_edge.urls")),
    path("api/v1/scalping/", include("scalping.urls")),
    path("api/v1/infrastructure/", include("infrastructure.urls")),
    path("api/v1/security/", include("security.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
