"""
URL configuration for API (REST Framework).
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views

# ── Root router ───────────────────────────────────────────────────────────────
router = DefaultRouter()
router.register(r'files', views.StorageFileViewSet, basename='file')
router.register(r'folders', views.StorageFolderViewSet, basename='folder')
router.register(r'shares', views.UserShareViewSet, basename='share')
router.register(r'public-links', views.PublicLinkViewSet, basename='public_link')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'activities', views.ActivityLogViewSet, basename='activity')
# Departments
router.register(r'departments', views.DepartmentViewSet, basename='department')
# Team Sites
router.register(r'team-sites', views.GroupShareViewSet, basename='team_site')
# Kanban
router.register(r'boards', views.TaskBoardViewSet, basename='board')
router.register(r'tasks', views.TaskViewSet, basename='task')
# News
router.register(r'news/categories', views.NewsCategoryViewSet, basename='news_category')
router.register(r'news/articles', views.NewsArticleViewSet, basename='news_article')
# Meetings
router.register(r'meetings', views.MeetingViewSet, basename='meeting')
# Messenger — Räume (list/create/retrieve/update/destroy + custom actions)
router.register(r'messenger/rooms', views.ChatRoomViewSet, basename='chat_room')

app_name = 'api'

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # ── Storage ───────────────────────────────────────────────────────────────
    path('storage/stats/', views.StorageStatsView.as_view(), name='storage_stats'),
    path('storage/quota/', views.StorageQuotaView.as_view(), name='storage_quota'),

    # File operations
    path('files/<int:file_id>/download/', views.FileDownloadAPIView.as_view(), name='file_download'),
    path('files/<int:file_id>/versions/', views.FileVersionsView.as_view(), name='file_versions'),
    path('files/<int:file_id>/restore/', views.RestoreFileVersionView.as_view(), name='restore_version'),

    # ── Search ────────────────────────────────────────────────────────────────
    path('search/', views.SearchAPIView.as_view(), name='search'),

    # ── Notifications ─────────────────────────────────────────────────────────
    path('notifications/', views.NotificationListView.as_view(), name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),

    # ── Share permissions ─────────────────────────────────────────────────────
    path('shares/<int:share_id>/permissions/', views.UpdateSharePermissionView.as_view(), name='update_share_permission'),
    path('public-links/<int:link_id>/password/', views.SetPublicLinkPasswordView.as_view(), name='set_link_password'),

    # ── Plugin management ─────────────────────────────────────────────────────
    path('plugins/discover/', views.PluginDiscoverView.as_view(), name='plugin_discover'),
    path('plugins/<uuid:plugin_id>/activate/', views.PluginActivateView.as_view(), name='plugin_activate'),
    path('plugins/<uuid:plugin_id>/deactivate/', views.PluginDeactivateView.as_view(), name='plugin_deactivate'),
    path('plugins/<uuid:plugin_id>/settings/', views.PluginSettingsView.as_view(), name='plugin_settings'),
    path('plugins/<uuid:plugin_id>/uninstall/', views.PluginUninstallView.as_view(), name='plugin_uninstall'),

    # ── Messenger — verschachtelte Nachrichten & Einladungen ──────────────────
    # Nachrichten
    path(
        'messenger/rooms/<int:room_pk>/messages/',
        views.ChatMessageViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='chat_message_list',
    ),
    path(
        'messenger/rooms/<int:room_pk>/messages/<int:pk>/',
        views.ChatMessageViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='chat_message_detail',
    ),
    path(
        'messenger/rooms/<int:room_pk>/messages/<int:pk>/react/',
        views.ChatMessageViewSet.as_view({'post': 'react'}),
        name='chat_message_react',
    ),
    # Einladungen erstellen (Owner/Admin)
    path(
        'messenger/rooms/<int:room_pk>/invites/',
        views.ChatInviteViewSet.as_view({'post': 'create'}),
        name='chat_invite_create',
    ),
    # Invite-Lookup & Annahme per Token
    path(
        'messenger/invites/<uuid:pk>/',
        views.ChatInviteViewSet.as_view({'get': 'retrieve'}),
        name='chat_invite_detail',
    ),
    path(
        'messenger/invites/<uuid:pk>/accept/',
        views.ChatInviteViewSet.as_view({'post': 'accept'}),
        name='chat_invite_accept',
    ),
    # Direktnachricht starten
    path('messenger/direct/', views.DirectMessageView.as_view(), name='messenger_direct'),
]
