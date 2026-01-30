"""
Django signals for Accounts app.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from accounts.models import UserProfile, AuditLog
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create UserProfile and root folder when new User is created.
    """
    if created:
        try:
            # Create user profile
            UserProfile.objects.create(user=instance)
            logger.info(f"Created user profile for: {instance.username}")

            # Create root folder for user
            from core.models import StorageFolder
            StorageFolder.objects.get_or_create(
                owner=instance,
                parent=None,
                defaults={'name': 'Root', 'description': 'Root folder'}
            )
            logger.info(f"Created root folder for: {instance.username}")
        except Exception as e:
            logger.error(f"Error creating user profile for {instance.username}: {str(e)}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save UserProfile when User is saved.
    """
    if hasattr(instance, 'profile'):
        try:
            instance.profile.save()
        except Exception as e:
            logger.error(f"Error saving user profile for {instance.username}: {str(e)}")


@receiver(post_save, sender=AuditLog)
def log_audit_action(sender, instance, created, **kwargs):
    """
    Log audit actions (can be extended for additional notifications).
    """
    if created and instance.action in ['2fa_enable', 'password_change']:
        logger.warning(
            f"Security event: {instance.user.username} - "
            f"{instance.get_action_display()} from {instance.ip_address}"
        )
