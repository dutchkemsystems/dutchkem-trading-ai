from django.urls import path

from . import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification_list"),
    path("<uuid:pk>/", views.NotificationDetailView.as_view(), name="notification_detail"),
    path("<uuid:notification_id>/read/", views.NotificationMarkReadView.as_view(), name="notification_mark_read"),
    path("read-all/", views.NotificationMarkAllReadView.as_view(), name="notification_mark_all_read"),
    path("unread-count/", views.NotificationUnreadCountView.as_view(), name="notification_unread_count"),
    path("preferences/", views.UserNotificationPreferenceView.as_view(), name="notification_preferences"),
]
