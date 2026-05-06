from django.shortcuts import redirect
from django.urls import reverse


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
