from django.urls import path

from . import views

app_name = 'infrastructure'

urlpatterns = [
    # Existing endpoints
    path('cluster/', views.cluster_status, name='cluster-status'),
    path('health/', views.health_checks, name='health-checks'),
    path('mt5-pool/', views.mt5_pool_status, name='mt5-pool-status'),
    path('sync/', views.sync_status, name='sync-status'),
    path('recovery/', views.force_health_check, name='force-recovery'),

    # V4 Always-On Resiliency endpoints
    path('status/', views.overall_status, name='overall-status'),
    path('system-health/', views.system_health, name='system-health'),
    path('nodes/', views.node_status, name='node-status'),
    path('failover/', views.trigger_failover, name='trigger-failover'),
    path('failover/status/', views.failover_status, name='failover-status'),
    path('failover/events/', views.failover_events, name='failover-events'),
    path('broker/status/', views.broker_failover_status, name='broker-failover-status'),
    path('broker/failover/', views.trigger_broker_failover, name='trigger-broker-failover'),
    path('power/', views.power_status, name='power-status'),
    path('internet/', views.internet_status, name='internet-status'),
    path('trading-state/', views.trading_state_status, name='trading-state-status'),
    path('trading-state/save/', views.save_trading_state, name='save-trading-state'),
    path('alerts/', views.recent_alerts, name='recent-alerts'),
]
