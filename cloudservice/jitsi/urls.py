from django.urls import path
from . import views

app_name = 'jitsi'

urlpatterns = [
    path('', views.meetings, name='meetings'),
    path('schedule/', views.schedule, name='schedule'),
    path('<int:pk>/start/', views.start_meeting, name='start_meeting'),
    path('<int:pk>/join/', views.join_meeting, name='join_meeting'),
    path('<int:pk>/room/', views.meeting_room, name='meeting_room'),
    path('<int:pk>/end/', views.end_meeting, name='end_meeting'),
    path('<int:pk>/cancel/', views.cancel_meeting, name='cancel_meeting'),
    path('join/', views.join, name='join'),
    path('join/<str:room>/', views.join, name='join_room'),
    path('api/token/', views.token_api, name='token_api'),
]
