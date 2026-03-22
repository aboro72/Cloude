"""
URL configuration for Core app.
"""

from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('landing/', views.landing, name='landing'),
    path('apps/<slug:slug>/', views.plugin_app, name='plugin_app'),
    path('activity/', views.activity_log, name='activity_log'),
    path('search/', views.search, name='search'),
    path('search/suggest/', views.search_suggest, name='search_suggest'),
    path('settings/', views.settings, name='settings'),
    path('help/', views.help_page, name='help'),
    path('help/developer/', views.help_developer, name='help_developer'),
    path('impressum/', views.impressum, name='impressum'),
    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/count/', views.notifications_unread_count, name='notifications_count'),
    path('notifications/mark-all/', views.notifications_mark_all_read, name='notifications_mark_all'),
    path('notifications/<int:pk>/read/', views.notifications_mark_read, name='notifications_mark_read'),
    path('notifications/dropdown/', views.notifications_dropdown, name='notifications_dropdown'),
]
