from django.core.management.base import BaseCommand, CommandError

from core.mongodb import ping


class Command(BaseCommand):
    help = "Prueft die konfigurierte MongoDB-Verbindung."

    def handle(self, *args, **options):
        result = ping()
        if result.get('ok'):
            self.stdout.write(self.style.SUCCESS(result['info']))
            return
        raise CommandError(result.get('info') or 'MongoDB nicht erreichbar')
