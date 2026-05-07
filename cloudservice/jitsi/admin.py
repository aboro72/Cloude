from django.contrib import admin
from .models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'organizer', 'status', 'scheduled_start', 'started_at', 'ended_at')
    list_filter = ('status', 'company')
    search_fields = ('title', 'organizer__username', 'organizer__first_name')
    filter_horizontal = ('invitees',)
    readonly_fields = ('room_name', 'started_at', 'ended_at', 'created_at', 'updated_at')
