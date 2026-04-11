"""
URL configuration for Sharing app.
"""

from django.urls import path
from sharing import views
from news.views import AddCommentView, ToggleReactionView

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
    path('groups/', views.GroupCompanyRedirectView.as_view(), name='groups_root'),
    path('firmen/<slug:company_slug>/teams/', views.GroupsListView.as_view(), name='groups_list'),
    path('firmen/<slug:company_slug>/teams/neu/', views.CreateGroupView.as_view(), name='create_group'),
    path('firmen/<slug:company_slug>/teams/<int:group_id>/', views.GroupDetailView.as_view(), name='group_detail'),
    path('firmen/<slug:company_slug>/teams/<int:group_id>/bearbeiten/', views.GroupUpdateView.as_view(), name='group_edit'),
    path('firmen/<slug:company_slug>/teams/<int:group_id>/news/', views.TeamSiteNewsListView.as_view(), name='team_news_list'),
    path('firmen/<slug:company_slug>/teams/<int:group_id>/news/neu/', views.TeamSiteNewsCreateView.as_view(), name='team_news_create'),
    path('firmen/<slug:company_slug>/teams/<int:group_id>/news/<int:news_id>/', views.TeamSiteNewsDetailView.as_view(), name='team_news_detail'),
    path('firmen/<slug:company_slug>/teams/<int:group_id>/news/<int:news_id>/bearbeiten/', views.TeamSiteNewsUpdateView.as_view(), name='team_news_edit'),
    path('firmen/<slug:company_slug>/teams/<int:group_id>/teilen/', views.GroupShareView.as_view(), name='group_share'),

    # Shared with me
    path('shared-with-me/', views.SharedWithMeView.as_view(), name='shared_with_me'),

    # AJAX comment & reaction endpoints (reuse news app views, generic FK)
    path('comment/add/', AddCommentView.as_view(), name='add_comment'),
    path('reaction/toggle/', ToggleReactionView.as_view(), name='toggle_reaction'),
]
