"""
Management command to create demo users for testing.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create demo users for testing'

    def handle(self, *args, **options):
        demo_users = [
            {
                'username': 'admin',
                'email': 'admin@cloudservice.local',
                'password': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
                'profile_role': 'admin',
            },
            {
                'username': 'demo',
                'email': 'demo@cloudservice.local',
                'password': 'demo',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_staff': False,
                'is_superuser': False,
                'profile_role': 'user',
            },
        ]

        for user_data in demo_users:
            username = user_data['username']
            password = user_data.pop('password')
            role = user_data.pop('profile_role')

            # Create or update user
            user, created = User.objects.get_or_create(
                username=username,
                defaults=user_data
            )

            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {username}')
                )
            else:
                # Update existing user
                for key, value in user_data.items():
                    setattr(user, key, value)
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.WARNING(f'Updated user: {username}')
                )

            # Ensure UserProfile exists
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            if role == 'admin':
                profile.storage_quota = 100 * 1024 * 1024 * 1024  # 100GB
            else:
                profile.storage_quota = 10 * 1024 * 1024 * 1024   # 10GB
            profile.save()

            self.stdout.write(
                self.style.SUCCESS(f'  Email: {user.email}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Password: {password}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Role: {role}')
            )

        self.stdout.write(
            self.style.SUCCESS('\nDemo users setup complete!')
        )
