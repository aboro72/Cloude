from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.backends import ModelBackend
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class PlatformJWTAuthentication(JWTAuthentication):
    """
    JWT authentication backend that validates tokens across all platform apps.
    Extends DRF's JWT authentication with platform-specific enhancements.
    """

    def get_user(self, validated_token):
        """
        Get user from validated JWT token.
        Adds platform-specific context.
        """
        user = super().get_user(validated_token)
        # Store which app issued the token (for logging/tracking)
        if 'app' in validated_token:
            user._jwt_app_source = validated_token['app']
        return user


class PlatformModelBackend(ModelBackend):
    """
    Custom authentication backend for platform authentication.
    Supports both email and username authentication.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate using email or username.
        """
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()

        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if username is None or password is None:
            return None

        try:
            # Try to find user by email first
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            try:
                # Fallback to username
                user = UserModel.objects.get(username=username)
            except UserModel.DoesNotExist:
                return None

        # Check password and active status
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def user_can_authenticate(self, user):
        """
        Check if user can authenticate (is active).
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None


class PlatformJWTTokenGenerator:
    """
    Generate JWT tokens with platform-wide claims.
    """

    @staticmethod
    def get_tokens_for_user(user, app_name=None):
        """
        Generate access and refresh tokens for a user.

        Args:
            user: User instance
            app_name: Name of the app requesting the token (optional)

        Returns:
            dict with 'refresh' and 'access' keys
        """
        refresh = RefreshToken.for_user(user)

        # Add custom claims
        refresh['email'] = user.email
        refresh['username'] = user.username
        refresh['role'] = user.role
        refresh['first_name'] = user.first_name
        refresh['last_name'] = user.last_name

        if app_name:
            refresh['app'] = app_name  # Track which app issued the token

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    @staticmethod
    def get_access_token_for_user(user, app_name=None):
        """
        Generate only an access token for a user.
        """
        tokens = PlatformJWTTokenGenerator.get_tokens_for_user(user, app_name)
        return tokens['access']
