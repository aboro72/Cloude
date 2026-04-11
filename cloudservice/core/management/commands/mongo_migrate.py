from django.core.management.base import BaseCommand, CommandError

from accounts.models import AuditLog
from core.models import ActivityLog
from core.mongo_audit import upsert_activity_log, upsert_audit_log, upsert_plugin_log
from core.mongodb import is_available, mongo_write_enabled
from plugins.models import PluginLog


class Command(BaseCommand):
    help = "Spiegelt nur die minimalen Hybrid-Daten nach MongoDB."

    def handle(self, *args, **options):
        if not is_available():
            raise CommandError("MongoDB ist nicht verfuegbar")

        self.stdout.write("Starte minimale Migration zu MongoDB...")
        counts = {
            'activity_logs': 0,
            'account_audit_logs': 0,
            'plugin_logs': 0,
        }

        if mongo_write_enabled('activity_logs'):
            for item in ActivityLog.objects.select_related('user', 'file', 'folder').iterator():
                upsert_activity_log(item)
                counts['activity_logs'] += 1

        if mongo_write_enabled('account_audit_logs'):
            for item in AuditLog.objects.select_related('user').iterator():
                upsert_audit_log(item)
                counts['account_audit_logs'] += 1

        if mongo_write_enabled('plugin_logs'):
            for item in PluginLog.objects.select_related('plugin', 'user').iterator():
                upsert_plugin_log(item)
                counts['plugin_logs'] += 1

        self.stdout.write(self.style.SUCCESS(
            f"MongoDB-Migration abgeschlossen: activity_logs={counts['activity_logs']}, "
            f"account_audit_logs={counts['account_audit_logs']}, plugin_logs={counts['plugin_logs']}"
        ))
