from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='platform_auth.User')
def user_created_signal(sender, instance, created, **kwargs):
    """
    Signal handler when a new user is created.
    Apps can listen to this signal to perform additional setup.
    """
    if created:
        logger.info(f'New user created: {instance.email}')
        # Apps can extend this by listening to the signal
        user_post_create.send(
            sender=sender,
            user=instance,
        )


# Custom signal for apps to listen to
from django.dispatch import Signal

user_post_create = Signal()
