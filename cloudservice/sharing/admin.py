from django.contrib import admin

from sharing.models import GroupShare, PublicLink, TeamSiteNews, UserShare


@admin.register(GroupShare)
class GroupShareAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'company', 'department', 'owner', 'permission', 'is_active', 'created_at')
    search_fields = ('group_name', 'owner__username', 'company__name', 'department__name')
    filter_horizontal = ('members', 'team_leaders')


@admin.register(TeamSiteNews)
class TeamSiteNewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'category', 'is_pinned', 'is_published', 'publish_at', 'author')
    list_filter = ('is_published', 'is_pinned', 'category')
    search_fields = ('title', 'summary', 'content', 'group__group_name')


@admin.register(UserShare)
class UserShareAdmin(admin.ModelAdmin):
    list_display = ('owner', 'shared_with', 'permission', 'is_active', 'created_at')
    list_filter = ('permission', 'is_active')
    search_fields = ('owner__username', 'shared_with__username')


@admin.register(PublicLink)
class PublicLinkAdmin(admin.ModelAdmin):
    list_display = ('token', 'owner', 'permission', 'is_active', 'view_count', 'download_count')
    list_filter = ('permission', 'is_active')
    search_fields = ('token', 'owner__username', 'title')
