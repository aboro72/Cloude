from django.contrib import admin

from departments.models import Department, DepartmentMembership


class MembershipInline(admin.TabularInline):
    model = DepartmentMembership
    extra = 0
    fields = ['user', 'role', 'joined_at']
    readonly_fields = ['joined_at']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'head', 'member_count', 'site_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MembershipInline]
    readonly_fields = ['created_at', 'created_by']


@admin.register(DepartmentMembership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'role', 'joined_at']
    list_filter = ['role', 'department']
    search_fields = ['user__username', 'department__name']
