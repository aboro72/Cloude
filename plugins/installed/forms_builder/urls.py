from django.urls import path
from forms_builder import views

app_name = 'forms_builder'

urlpatterns = [
    path('new/', views.form_create, name='form_create'),
    path('<int:form_id>/build/', views.form_build, name='form_build'),
    path('<int:form_id>/fill/', views.form_fill, name='form_fill'),
    path('<int:form_id>/results/', views.form_results, name='form_results'),
    path('<int:form_id>/export/', views.form_export_csv, name='form_export'),
    path('<int:form_id>/toggle/', views.form_toggle, name='form_toggle'),
    path('<int:form_id>/delete/', views.form_delete, name='form_delete'),
    # Field AJAX
    path('<int:form_id>/field/add/', views.field_add, name='field_add'),
    path('field/<int:field_id>/delete/', views.field_delete, name='field_delete'),
    path('field/<int:field_id>/update/', views.field_update, name='field_update'),
    path('<int:form_id>/field/reorder/', views.field_reorder, name='field_reorder'),
]
