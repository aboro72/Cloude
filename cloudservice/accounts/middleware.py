import ipaddress
import logging

from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        # Erstes Element ist die echte Client-IP (bei korrektem nginx-Setup)
        ip = xff.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        return request.META.get('REMOTE_ADDR', '')


class SecurityHeadersMiddleware:
    """Setzt sicherheitsrelevante HTTP-Response-Header die Django nicht automatisch setzt."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('X-Frame-Options', 'DENY')
        response.setdefault('X-XSS-Protection', '1; mode=block')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        if not settings.DEBUG:
            response.setdefault(
                'Strict-Transport-Security',
                'max-age=15768000; includeSubDomains; preload'
            )
        return response


class AdminIPAllowlistMiddleware:
    """Blockiert Zugriff auf /admin/ für IPs die nicht auf der Allowlist stehen.
    Wird nur aktiv wenn ADMIN_IP_ALLOWLIST in settings gesetzt ist."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.allowlist = getattr(settings, 'ADMIN_IP_ALLOWLIST', [])

    def __call__(self, request):
        if self.allowlist and request.path.startswith('/admin/'):
            client_ip = _get_client_ip(request)
            if not self._is_allowed(client_ip):
                logger.warning(
                    'Admin-Zugriff blockiert von IP %s auf %s', client_ip, request.path
                )
                return HttpResponseForbidden('Zugriff verweigert.')
        return self.get_response(request)

    def _is_allowed(self, ip):
        try:
            client = ipaddress.ip_address(ip)
        except ValueError:
            return False
        for entry in self.allowlist:
            entry = entry.strip()
            if not entry:
                continue
            try:
                if '/' in entry:
                    if client in ipaddress.ip_network(entry, strict=False):
                        return True
                else:
                    if client == ipaddress.ip_address(entry):
                        return True
            except ValueError:
                continue
        return False


class BruteForceLoginMiddleware:
    """Sperrt IPs nach zu vielen fehlgeschlagenen Login-Versuchen temporär aus.

    Zählt fehlgeschlagene POSTs auf /accounts/login/ und blockiert die IP
    für FAILED_LOGIN_LOCKOUT_MINUTES Minuten nach MAX_FAILED_LOGINS Fehlern.
    """

    LOGIN_URL_NAMES = ['/accounts/login/', '/api/auth/token/']

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_attempts = getattr(settings, 'MAX_FAILED_LOGINS', 5)
        self.lockout_minutes = getattr(settings, 'FAILED_LOGIN_LOCKOUT_MINUTES', 15)

    def __call__(self, request):
        if request.method == 'POST' and any(
            request.path.startswith(url) for url in self.LOGIN_URL_NAMES
        ):
            ip = _get_client_ip(request)
            lock_key = f'login_lock:{ip}'
            if cache.get(lock_key):
                logger.warning('Gesperrte IP %s versucht Login-Zugriff', ip)
                return HttpResponseForbidden(
                    f'Zu viele fehlgeschlagene Login-Versuche. '
                    f'Bitte warte {self.lockout_minutes} Minuten.'
                )

        response = self.get_response(request)

        # Fehlgeschlagene Logins tracken (401 auf Token-Endpoint, 200 mit Fehler auf Login-View)
        if request.method == 'POST':
            ip = _get_client_ip(request)
            is_login_path = any(
                request.path.startswith(url) for url in self.LOGIN_URL_NAMES
            )
            if is_login_path and response.status_code in (400, 401, 403):
                fail_key = f'login_fail:{ip}'
                fails = cache.get(fail_key, 0) + 1
                cache.set(fail_key, fails, timeout=self.lockout_minutes * 60)
                if fails >= self.max_attempts:
                    lock_key = f'login_lock:{ip}'
                    cache.set(lock_key, True, timeout=self.lockout_minutes * 60)
                    logger.warning(
                        'IP %s gesperrt nach %d fehlgeschlagenen Login-Versuchen',
                        ip, fails
                    )

        return response


class ForcePasswordChangeMiddleware:
    """Leitet Benutzer zur Passwort-Änderung weiter wenn must_change_password gesetzt ist."""

    EXEMPT_URLS = None

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._must_redirect(request):
            return redirect(reverse('accounts:password_change'))
        return self.get_response(request)

    def _must_redirect(self, request):
        if not request.user.is_authenticated:
            return False

        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.must_change_password:
            return False

        # Erlaubte URLs während Passwort-Pflicht
        allowed = [
            reverse('accounts:password_change'),
            reverse('accounts:logout'),
        ]
        return request.path not in allowed
