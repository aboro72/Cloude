"""
URL configuration for API (REST Framework).
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views

# Create router
router = DefaultRouter()
router.register(r'files', views.StorageFileViewSet, basename='file')
router.register(r'folders', views.StorageFolderViewSet, basename='folder')
router.register(r'shares', views.UserShareViewSet, basename='share')
router.register(r'public-links', views.PublicLinkViewSet, basename='public_link')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'activities', views.ActivityLogViewSet, basename='activity')

app_name = 'api'

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Custom endpoints
    path('storage/stats/', views.StorageStatsView.as_view(), name='storage_stats'),
    path('storage/quota/', views.StorageQuotaView.as_view(), name='storage_quota'),

    # File operations
    path('files/<int:file_id>/download/', views.FileDownloadAPIView.as_view(), name='file_download'),
    path('files/<int:file_id>/versions/', views.FileVersionsView.as_view(), name='file_versions'),
    path('files/<int:file_id>/restore/', views.RestoreFileVersionView.as_view(), name='restore_version'),

    # Search
    path('search/', views.SearchAPIView.as_view(), name='search'),

    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),

    # Share permissions
    path('shares/<int:share_id>/permissions/', views.UpdateSharePermissionView.as_view(), name='update_share_permission'),
    path('public-links/<int:link_id>/password/', views.SetPublicLinkPasswordView.as_view(), name='set_link_password'),

    # Plugin management
    path('plugins/<uuid:plugin_id>/activate/', views.PluginActivateView.as_view(), name='plugin_activate'),
    path('plugins/<uuid:plugin_id>/deactivate/', views.PluginDeactivateView.as_view(), name='plugin_deactivate'),
]
