from django.urls import path
from messenger import views

app_name = 'messenger'

urlpatterns = [
    path('', views.messenger_home, name='home'),
    path('channel/create/', views.create_channel, name='create_channel'),
    path('channel/<slug:room_slug>/', views.room_view, name='room'),
    path('channel/<slug:room_slug>/invite/', views.invite_create, name='invite_create'),
    path('channel/<slug:room_slug>/join/', views.room_join, name='room_join'),
    path('dm/<str:username>/', views.direct_message, name='direct_message'),
    path('messages/<int:room_id>/load/', views.messages_load, name='messages_load'),
    path('unread/', views.messenger_unread_count, name='unread_count'),
]
