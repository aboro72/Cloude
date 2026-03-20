from django.urls import path

from departments import views

app_name = 'departments'

urlpatterns = [
    path('', views.DepartmentListView.as_view(), name='list'),
    path('neu/', views.DepartmentCreateView.as_view(), name='create'),
    path('<slug:slug>/', views.DepartmentDetailView.as_view(), name='detail'),
    path('<slug:slug>/bearbeiten/', views.DepartmentEditView.as_view(), name='edit'),
    path('<slug:slug>/loeschen/', views.DepartmentDeleteView.as_view(), name='delete'),
    path('<slug:slug>/mitglieder/hinzufuegen/', views.DepartmentMemberAddView.as_view(), name='member_add'),
    path('<slug:slug>/mitglieder/entfernen/', views.DepartmentMemberRemoveView.as_view(), name='member_remove'),
    path('<slug:slug>/mitglieder/rolle/', views.DepartmentMemberRoleView.as_view(), name='member_role'),
    path('<slug:slug>/team-sites/', views.DepartmentSiteAssignView.as_view(), name='assign_sites'),
]
