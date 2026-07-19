from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from core.models import Notification
from jitsi.models import Meeting


@receiver(m2m_changed, sender=Meeting.invitees.through)
def notify_meeting_invitees(sender, instance, action, pk_set, **kwargs):
    if action != 'post_add' or not pk_set:
        return
    organizer = instance.organizer.get_full_name() or instance.organizer.username
    for invitee in instance.invitees.filter(pk__in=pk_set, is_active=True):
        Notification.notify(
            user=invitee,
            notification_type='message',
            title=f'Meeting-Einladung: {instance.title}',
            message=f'{organizer} hat dich zu einem Meeting eingeladen.',
            url='/meetings/',
        )
