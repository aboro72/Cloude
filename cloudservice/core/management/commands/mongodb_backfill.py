from django.core.management.base import BaseCommand, CommandError

from accounts.models import AuditLog
from core.models import ActivityLog
from core.mongo_audit import upsert_activity_log, upsert_audit_log, upsert_plugin_log
from core.mongodb import is_available, mongo_write_enabled
from plugins.models import PluginLog


class Command(BaseCommand):
    help = "Spiegelt nur die fuer den Hybrid-Betrieb freigegebenen MongoDB-Collections nach MongoDB."

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        if not is_available():
            raise CommandError('MongoDB ist nicht verfuegbar.')

        batch_size = options['batch_size']
        counts = {
            'activity_logs': 0,
            'account_audit_logs': 0,
            'plugin_logs': 0,
        }

        if mongo_write_enabled('activity_logs'):
            for item in ActivityLog.objects.select_related('user', 'file', 'folder').iterator(chunk_size=batch_size):
                upsert_activity_log(item)
                counts['activity_logs'] += 1

        if mongo_write_enabled('account_audit_logs'):
            for item in AuditLog.objects.select_related('user').iterator(chunk_size=batch_size):
                upsert_audit_log(item)
                counts['account_audit_logs'] += 1

        if mongo_write_enabled('plugin_logs'):
            for item in PluginLog.objects.select_related('plugin', 'user').iterator(chunk_size=batch_size):
                upsert_plugin_log(item)
                counts['plugin_logs'] += 1

        self.stdout.write(self.style.SUCCESS(
            f"MongoDB Backfill OK: activity_logs={counts['activity_logs']}, "
            f"account_audit_logs={counts['account_audit_logs']}, plugin_logs={counts['plugin_logs']}"
        ))
