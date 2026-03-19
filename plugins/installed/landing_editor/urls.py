from django.urls import path
from landing_editor import views

app_name = 'landing_editor'

urlpatterns = [
    path('save/', views.save_settings, name='save'),
]
