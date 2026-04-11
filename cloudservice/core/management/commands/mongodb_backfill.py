from django.core.management.base import BaseCommand, CommandError

from accounts.models import AuditLog
from core.models import ActivityLog, Notification
from core.mongo_audit import (
    upsert_activity_log,
    upsert_audit_log,
    upsert_notification,
    upsert_plugin_log,
    upsert_team_news,
)
from core.mongodb import is_available
from plugins.models import PluginLog
from sharing.models import TeamSiteNews


class Command(BaseCommand):
    help = "Spiegelt bestehende ActivityLogs, AuditLogs und Notifications nach MongoDB."

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        if not is_available():
            raise CommandError('MongoDB ist nicht verfuegbar.')

        batch_size = options['batch_size']
        counts = {
            'activity_logs': 0,
            'audit_logs': 0,
            'notifications': 0,
            'team_news': 0,
            'plugin_logs': 0,
        }

        for item in ActivityLog.objects.select_related('user', 'file', 'folder').iterator(chunk_size=batch_size):
            upsert_activity_log(item)
            counts['activity_logs'] += 1

        for item in AuditLog.objects.select_related('user').iterator(chunk_size=batch_size):
            upsert_audit_log(item)
            counts['audit_logs'] += 1

        for item in Notification.objects.select_related('user').iterator(chunk_size=batch_size):
            upsert_notification(item)
            counts['notifications'] += 1

        for item in TeamSiteNews.objects.select_related('group__company', 'group__department', 'author').iterator(chunk_size=batch_size):
            upsert_team_news(item)
            counts['team_news'] += 1

        for item in PluginLog.objects.select_related('plugin', 'user').iterator(chunk_size=batch_size):
            upsert_plugin_log(item)
            counts['plugin_logs'] += 1

        self.stdout.write(self.style.SUCCESS(
            f"MongoDB Backfill OK: activity_logs={counts['activity_logs']}, "
            f"audit_logs={counts['audit_logs']}, notifications={counts['notifications']}, "
            f"team_news={counts['team_news']}, plugin_logs={counts['plugin_logs']}"
        ))
