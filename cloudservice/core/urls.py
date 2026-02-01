"""
URL configuration for Core app.
"""

from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('landing/', views.landing, name='landing'),
    path('activity/', views.activity_log, name='activity_log'),
    path('search/', views.search, name='search'),
    path('settings/', views.settings, name='settings'),
    path('help/', views.help_page, name='help'),
    path('help/developer/', views.help_developer, name='help_developer'),
]
