from django.utils.functional import SimpleLazyObject
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging

logger = logging.getLogger(__name__)


class PlatformJWTMiddleware:
    """
    Middleware to authenticate users via JWT across all platform apps.
    Works alongside Django's session authentication.

    Allows both Bearer token authentication and cookie-based token storage.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Try JWT authentication first
        request.user = SimpleLazyObject(lambda: self._get_user(request))
        return self.get_response(request)

    def _get_user(self, request):
        """
        Get user from JWT token or session.
        Priority:
        1. Authorization header (Bearer token)
        2. Cookie-based token
        3. Session authentication
        """
        # Try Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            user = self._get_user_from_token(auth_header[7:])
            if user:
                return user

        # Try cookie-based token
        token = request.COOKIES.get('platform_sso_token')
        if token:
            user = self._get_user_from_token(token)
            if user:
                return user

        # Fall back to session authentication
        from django.contrib.auth.middleware import get_user
        return get_user(request)

    def _get_user_from_token(self, token):
        """Extract user from JWT token"""
        try:
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()

            access_token = AccessToken(token)
            user_id = access_token['user_id']

            try:
                user = UserModel.objects.get(id=user_id, is_active=True)
                return user
            except UserModel.DoesNotExist:
                logger.warning(f'User {user_id} not found or inactive')
                return AnonymousUser()
        except (TokenError, InvalidToken):
            # Token is invalid or expired
            return None
        except Exception as e:
            logger.error(f'Error extracting user from token: {str(e)}')
            return None


class ActivityTrackingMiddleware:
    """
    Middleware to track user activity for online status.
    Updates last_activity timestamp periodically.
    """

    # Update interval in minutes (to avoid excessive database writes)
    UPDATE_INTERVAL = 1

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Update activity for authenticated users
        if request.user and request.user.is_authenticated:
            self._update_activity(request.user)

        return response

    def _update_activity(self, user):
        """Update user activity timestamp"""
        from django.utils import timezone
        from datetime import timedelta

        # Only update if last_activity is older than UPDATE_INTERVAL
        if user.last_activity:
            time_since_update = timezone.now() - user.last_activity
            if time_since_update < timedelta(minutes=self.UPDATE_INTERVAL):
                return

        try:
            user.update_activity()
        except Exception as e:
            logger.error(f'Error updating user activity: {str(e)}')
