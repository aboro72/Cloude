from django.urls import path
from tasks_board import views

app_name = 'tasks_board'

urlpatterns = [
    path('board/new/', views.board_create, name='board_create'),
    path('board/<int:board_id>/', views.board_detail, name='board_detail'),
    path('board/<int:board_id>/delete/', views.board_delete, name='board_delete'),
    # Task AJAX
    path('board/<int:board_id>/task/add/', views.task_add, name='task_add'),
    path('task/<int:task_id>/update/', views.task_update, name='task_update'),
    path('task/<int:task_id>/move/', views.task_move, name='task_move'),
    path('task/<int:task_id>/delete/', views.task_delete, name='task_delete'),
    path('task/<int:task_id>/reorder/', views.task_reorder, name='task_reorder'),
]
