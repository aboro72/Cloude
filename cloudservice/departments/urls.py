from django.urls import path

from departments import views

app_name = 'departments'

urlpatterns = [
    path('', views.DepartmentCompanyRedirectView.as_view(), name='root'),
    path('firmen/', views.CompanyListView.as_view(), name='company_list'),
    path('firmen/neu/', views.CompanyCreateView.as_view(), name='company_create'),
    path('firmen/<slug:company_slug>/verwaltung/', views.CompanyDetailView.as_view(), name='company_detail'),
    path('firmen/<slug:company_slug>/verwaltung/bearbeiten/', views.CompanyEditView.as_view(), name='company_edit'),
    path('firmen/<slug:company_slug>/verwaltung/einladungen/neu/', views.CompanyInvitationCreateView.as_view(), name='company_invite_create'),
    path('firmen/<slug:company_slug>/verwaltung/einladungen/<int:invitation_id>/sperren/', views.CompanyInvitationRevokeView.as_view(), name='company_invite_revoke'),
    path('firmen/<slug:company_slug>/', views.DepartmentListView.as_view(), name='list'),
    path('firmen/<slug:company_slug>/neu/', views.DepartmentCreateView.as_view(), name='create'),
    path('firmen/<slug:company_slug>/<slug:slug>/', views.DepartmentDetailView.as_view(), name='detail'),
    path('firmen/<slug:company_slug>/<slug:slug>/bearbeiten/', views.DepartmentEditView.as_view(), name='edit'),
    path('firmen/<slug:company_slug>/<slug:slug>/loeschen/', views.DepartmentDeleteView.as_view(), name='delete'),
    path('firmen/<slug:company_slug>/<slug:slug>/mitglieder/hinzufuegen/', views.DepartmentMemberAddView.as_view(), name='member_add'),
    path('firmen/<slug:company_slug>/<slug:slug>/mitglieder/entfernen/', views.DepartmentMemberRemoveView.as_view(), name='member_remove'),
    path('firmen/<slug:company_slug>/<slug:slug>/mitglieder/rolle/', views.DepartmentMemberRoleView.as_view(), name='member_role'),
    path('firmen/<slug:company_slug>/<slug:slug>/team-sites/', views.DepartmentSiteAssignView.as_view(), name='assign_sites'),
]
