from django.urls import path

from . import views

urlpatterns = [
    path("timeframes/", views.TimeframeListView.as_view(), name="timeframe_list"),
    path("timeframes/<uuid:pk>/", views.TimeframeDetailView.as_view(), name="timeframe_detail"),
    path("categories/", views.IndicatorCategoryListView.as_view(), name="indicator_category_list"),
    path("", views.IndicatorListView.as_view(), name="indicator_list"),
    path("<uuid:pk>/", views.IndicatorDetailView.as_view(), name="indicator_detail"),
    path("values/", views.IndicatorValueListView.as_view(), name="indicator_value_list"),
    path("configs/", views.TimeframeIndicatorConfigView.as_view(), name="timeframe_indicator_config"),
    path("calculate/", views.IndicatorCalculationView.as_view(), name="indicator_calculation"),
]
