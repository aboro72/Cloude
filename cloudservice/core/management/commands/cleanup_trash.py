"""
Management command to cleanup expired trash items.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from storage.models import TrashBin
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Delete expired trash items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete items older than this many days',
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timezone.timedelta(days=days)

        expired_items = TrashBin.objects.filter(expires_at__lt=cutoff_date)
        count = expired_items.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired items to delete'))
            return

        # Delete items
        for item in expired_items:
            try:
                item.delete()
            except Exception as e:
                logger.error(f"Error deleting trash item {item.id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f'Error deleting item {item.id}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {count} expired items')
        )
