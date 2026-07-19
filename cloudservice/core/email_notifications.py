import logging
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def absolute_url(path=''):
    base = getattr(settings, 'CLOUDSERVICE_EXTERNAL_URL', 'https://cloudshare.aborosoft.com')
    return urljoin(base.rstrip('/') + '/', path.lstrip('/'))


def send_user_email(user, subject, message, url=''):
    if not user or not user.is_active or not user.email:
        return False
    body = f"Hallo {user.get_full_name() or user.username},\n\n{message}"
    if url:
        body += f"\n\nDirekt öffnen: {absolute_url(url)}"
    body += "\n\nViele Grüße\nCloudShare"
    try:
        return bool(send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email]))
    except Exception:
        logger.exception('E-Mail-Benachrichtigung an Benutzer %s fehlgeschlagen', user.pk)
        return False


def send_welcome_email(user, initial_password):
    return send_user_email(
        user,
        'Dein CloudShare-Zugang',
        'Dein Benutzerkonto wurde angelegt.\n\n'
        f'Benutzername: {user.username}\n'
        f'Erstpasswort: {initial_password}\n\n'
        'Bitte ändere das Erstpasswort direkt nach der ersten Anmeldung.',
        '/accounts/login/',
    )
