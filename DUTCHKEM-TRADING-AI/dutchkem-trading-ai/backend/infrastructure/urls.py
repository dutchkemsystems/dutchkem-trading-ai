from django.urls import path

from . import views

app_name = 'infrastructure'

urlpatterns = [
    path('cluster/', views.cluster_status, name='cluster-status'),
    path('health/', views.health_checks, name='health-checks'),
    path('mt5-pool/', views.mt5_pool_status, name='mt5-pool-status'),
    path('sync/', views.sync_status, name='sync-status'),
    path('recovery/', views.force_health_check, name='force-recovery'),
]
