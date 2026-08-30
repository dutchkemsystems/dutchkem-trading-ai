from django.urls import path

from . import views

app_name = 'scalping'

urlpatterns = [
    path('scanner/', views.scanner_status, name='scanner-status'),
    path('opportunities/', views.top_opportunities, name='top-opportunities'),
    path('spikes/', views.spike_history, name='spike-history'),
    path('news/', views.news_events, name='news-events'),
    path('check-pause/', views.check_pause, name='check-pause'),
]
