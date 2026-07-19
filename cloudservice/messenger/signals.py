from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Notification
from core.email_notifications import absolute_url
from messenger.models import ChatInvite, ChatMessage


@receiver(post_save, sender=ChatInvite)
def email_chat_invite(sender, instance, created, **kwargs):
    if not created or not instance.invited_email:
        return
    inviter = instance.invited_by.get_full_name() or instance.invited_by.username
    invite_url = absolute_url(f'/messenger/invite/{instance.token}/')
    send_mail(
        f'Einladung zum Chat „{instance.room.name}"',
        f'{inviter} hat dich zum Chat „{instance.room.name}" eingeladen.\n\n'
        f'Einladung annehmen: {invite_url}\n\nViele Grüße\nCloudShare',
        settings.DEFAULT_FROM_EMAIL,
        [instance.invited_email],
        fail_silently=True,
    )


@receiver(post_save, sender=ChatMessage)
def notify_chat_members(sender, instance, created, **kwargs):
    if not created or not instance.author or instance.message_type == 'system':
        return
    author = instance.author.get_full_name() or instance.author.username
    url = f'/{instance.room.company.workspace_key}/messenger/channel/{instance.room.slug}/'
    preview = instance.content.strip()[:240] or 'Neue Datei oder Nachricht'
    recipients = instance.room.memberships.filter(
        is_muted=False, user__is_active=True
    ).exclude(user=instance.author).select_related('user')
    for membership in recipients.iterator():
        Notification.notify(
            user=membership.user,
            notification_type='message',
            title=f'Neue Nachricht von {author}',
            message=f'{instance.room.name}: {preview}',
            url=url,
        )
