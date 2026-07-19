"""
Custom throttle classes for abuse prevention.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, SimpleRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """5 Login-Versuche pro Minute je IP – verhindert Brute-Force."""
    scope = 'login'
    rate = '5/min'


class PasswordResetThrottle(AnonRateThrottle):
    """3 Password-Reset-Anfragen pro Stunde je IP."""
    scope = 'password_reset'
    rate = '3/hour'


class FileUploadThrottle(UserRateThrottle):
    """50 Uploads pro Stunde je Nutzer – verhindert Quota-Flooding."""
    scope = 'upload'
    rate = '50/hour'


class PublicLinkThrottle(AnonRateThrottle):
    """20 Public-Link-Zugriffe pro Minute je IP – verhindert Token-Brute-Force."""
    scope = 'public_link'
    rate = '20/min'


class PublicLinkDownloadThrottle(AnonRateThrottle):
    """10 Downloads per Minute je IP über Public-Links."""
    scope = 'public_link_download'
    rate = '10/min'


class BurstAnonThrottle(AnonRateThrottle):
    """Kurzzeit-Limit für anonyme Requests: 30 pro Minute."""
    scope = 'anon_burst'
    rate = '30/min'


class BurstUserThrottle(UserRateThrottle):
    """Kurzzeit-Limit für authentifizierte Nutzer: 120 pro Minute."""
    scope = 'user_burst'
    rate = '120/min'
