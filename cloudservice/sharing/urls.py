"""
URL configuration for Sharing app.
"""

from django.urls import path
from sharing import views

app_name = 'sharing'

urlpatterns = [
    # User sharing
    path('share/<str:content_type>/<int:object_id>/', views.ShareView.as_view(), name='share'),
    path('shares/', views.SharesListView.as_view(), name='shares_list'),
    path('share/<int:share_id>/delete/', views.DeleteShareView.as_view(), name='delete_share'),

    # Public links
    path('public/<str:token>/', views.PublicLinkView.as_view(), name='public_link'),
    path('public/<str:token>/download/', views.PublicDownloadView.as_view(), name='public_download'),
    path('links/', views.PublicLinksListView.as_view(), name='links_list'),
    path('link/create/<str:content_type>/<int:object_id>/', views.CreatePublicLinkView.as_view(), name='create_link'),
    path('link/<int:pk>/created/', views.LinkCreatedView.as_view(), name='link_created'),
    path('link/<int:link_id>/settings/', views.PublicLinkSettingsView.as_view(), name='link_settings'),
    path('link/<int:link_id>/delete/', views.DeletePublicLinkView.as_view(), name='delete_link'),

    # Group sharing
    path('groups/', views.GroupsListView.as_view(), name='groups_list'),
    path('group/create/', views.CreateGroupView.as_view(), name='create_group'),
    path('group/<int:group_id>/share/', views.GroupShareView.as_view(), name='group_share'),

    # Shared with me
    path('shared-with-me/', views.SharedWithMeView.as_view(), name='shared_with_me'),
]
