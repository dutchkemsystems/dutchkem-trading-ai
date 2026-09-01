from django.urls import path

from . import views

app_name = 'security'

urlpatterns = [
    path('status/', views.security_status, name='security-status'),
    path('events/', views.security_events, name='security-events'),
    path('threats/', views.threat_summary, name='threat-summary'),
    path('rotate-keys/', views.rotate_encryption_keys, name='rotate-keys'),
    path('blocked-ips/', views.blocked_ips, name='blocked-ips'),
]
