from django.contrib import admin

from departments.models import Company, CompanyInvitation, Department, DepartmentMembership


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'owner', 'employee_count', 'area_count', 'team_count', 'is_free_tier', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['admins']


class MembershipInline(admin.TabularInline):
    model = DepartmentMembership
    extra = 0
    fields = ['user', 'role', 'joined_at']
    readonly_fields = ['joined_at']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'head', 'member_count', 'site_count', 'created_at']
    list_filter = ['company', 'created_at']
    search_fields = ['name', 'description', 'company__name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MembershipInline]
    readonly_fields = ['created_at', 'created_by']


@admin.register(DepartmentMembership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'role', 'joined_at']
    list_filter = ['role', 'department']
    search_fields = ['user__username', 'department__name']


@admin.register(CompanyInvitation)
class CompanyInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'company', 'role', 'department', 'is_active', 'accepted_at', 'expires_at', 'created_at']
    list_filter = ['company', 'role', 'is_active', 'created_at']
    search_fields = ['email', 'company__name', 'department__name', 'token']
