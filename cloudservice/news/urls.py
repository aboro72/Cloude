from django.urls import path

from news import views

app_name = 'news'

urlpatterns = [
    path('', views.NewsListView.as_view(), name='news_list'),
    path('create/', views.NewsCreateView.as_view(), name='news_create'),
    path('comment/add/', views.AddCommentView.as_view(), name='add_comment'),
    path('reaction/toggle/', views.ToggleReactionView.as_view(), name='toggle_reaction'),
    path('<slug:slug>/', views.NewsDetailView.as_view(), name='news_detail'),
    path('<slug:slug>/edit/', views.NewsUpdateView.as_view(), name='news_edit'),
    path('<slug:slug>/delete/', views.NewsDeleteView.as_view(), name='news_delete'),
]
