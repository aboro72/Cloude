"""
Management command to reset the demo user's password.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Reset the demo user password to "demo".'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='demo')
        except User.DoesNotExist as exc:
            raise CommandError('User "demo" does not exist.') from exc

        user.set_password('demo')
        user.save(update_fields=['password'])
        self.stdout.write(self.style.SUCCESS('Password for user "demo" reset to "demo".'))
