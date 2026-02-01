"""
URL configuration for Storage app.
"""

from django.urls import path
from storage import views

app_name = 'storage'

urlpatterns = [
    # File browsing
    path('', views.FileListView.as_view(), name='file_list'),
    path('folder/<int:folder_id>/', views.FolderView.as_view(), name='folder'),
    path('file/<int:file_id>/', views.FileDetailView.as_view(), name='file_detail'),

    # File operations
    path('create/', views.CreateFileView.as_view(), name='create_file'),
    path('upload/', views.FileUploadView.as_view(), name='upload'),
    path('file/<int:file_id>/download/', views.FileDownloadView.as_view(), name='download'),
    path('file/<int:file_id>/rename/', views.FileRenameView.as_view(), name='rename'),
    path('file/<int:file_id>/move/', views.FileMoveView.as_view(), name='move'),
    path('file/<int:file_id>/delete/', views.FileDeleteView.as_view(), name='delete'),

    # Folder operations
    path('folder/create/', views.FolderCreateView.as_view(), name='create_folder'),
    path('folder/<int:folder_id>/delete/', views.FolderDeleteView.as_view(), name='delete_folder'),

    # Versioning
    path('file/<int:file_id>/versions/', views.FileVersionsView.as_view(), name='file_versions'),
    path('file/<int:file_id>/restore/<int:version_id>/', views.RestoreVersionView.as_view(), name='restore_version'),

    # Trash
    path('trash/', views.TrashView.as_view(), name='trash'),
    path('trash/<int:file_id>/restore/', views.RestoreFromTrashView.as_view(), name='restore_trash'),
    path('trash/<int:file_id>/delete/', views.PermanentlyDeleteView.as_view(), name='permanently_delete'),
    path('trash/empty/', views.EmptyTrashView.as_view(), name='empty_trash'),

    # Search
    path('search/', views.SearchView.as_view(), name='search'),

    # Stats
    path('stats/', views.StorageStatsView.as_view(), name='stats'),
]
