from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import logging

from .serializers import (
    UserDetailSerializer, UserProfileSerializer,
    PasswordChangeSerializer, PlatformTokenObtainPairSerializer
)
from .backends import PlatformJWTTokenGenerator

User = get_user_model()
logger = logging.getLogger(__name__)


class PlatformTokenObtainPairView(TokenObtainPairView):
    """
    API endpoint for obtaining JWT tokens.
    Extends DRF's TokenObtainPairView with platform customization.
    """
    serializer_class = PlatformTokenObtainPairSerializer
    permission_classes = [AllowAny]


class LoginView(APIView):
    """
    User login endpoint.
    Accepts email or username with password.
    Returns JWT tokens and user information.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Login user and return JWT tokens.

        Request body:
        {
            "email": "user@example.com" or "username": "john_doe",
            "password": "password123",
            "app_name": "cloude" (optional)
        }
        """
        email_or_username = request.data.get('email') or request.data.get('username')
        password = request.data.get('password')
        app_name = request.data.get('app_name', 'platform')

        if not email_or_username or not password:
            return Response(
                {'error': _('Email/username and password are required')},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate user
        user = authenticate(request, username=email_or_username, password=password)

        if user is None:
            logger.warning(f'Failed login attempt for {email_or_username}')
            return Response(
                {'error': _('Invalid credentials')},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': _('User account is inactive')},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate JWT tokens
        tokens = PlatformJWTTokenGenerator.get_tokens_for_user(user, app_name)

        # Log successful login
        user.last_login = __import__('django.utils.timezone', fromlist=['now']).now()
        user.save(update_fields=['last_login'])
        logger.info(f'User {user.email} logged in via {app_name}')

        response = Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': UserDetailSerializer(user).data,
        })

        # Set SSO cookie
        self._set_sso_cookie(response, tokens['access'])

        return response

    def _set_sso_cookie(self, response, token):
        """Set SSO cookie for domain-wide authentication"""
        response.set_cookie(
            key=getattr(settings, 'SSO_COOKIE_NAME', 'platform_sso_token'),
            value=token,
            domain=getattr(settings, 'SSO_COOKIE_DOMAIN', None),
            secure=getattr(settings, 'SSO_COOKIE_SECURE', True),
            httponly=True,
            samesite=getattr(settings, 'SSO_COOKIE_SAMESITE', 'Lax'),
            max_age=3600,  # 1 hour
        )


class LogoutView(APIView):
    """
    User logout endpoint.
    Optionally blacklists the current token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Logout user and clear SSO cookie"""
        logger.info(f'User {request.user.email} logged out')

        response = Response(
            {'message': _('Logged out successfully')},
            status=status.HTTP_200_OK
        )

        # Clear SSO cookie
        response.delete_cookie(
            key=getattr(settings, 'SSO_COOKIE_NAME', 'platform_sso_token'),
            domain=getattr(settings, 'SSO_COOKIE_DOMAIN', None)
        )

        return response


class UserProfileView(APIView):
    """
    User profile endpoint.
    GET: Retrieve current user profile
    PUT: Update current user profile
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve current user profile"""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """Update current user profile"""
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                UserDetailSerializer(request.user).data,
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    Password change endpoint.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Change user password"""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            logger.info(f'User {request.user.email} changed password')
            return Response(
                {'message': _('Password changed successfully')},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HealthCheckView(APIView):
    """
    Health check endpoint.
    Used by load balancers and monitoring.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Check system health"""
        from django.db import connection

        health_status = {
            'status': 'healthy',
            'database': 'ok',
            'cache': 'ok',
        }

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['database'] = str(e)
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Check cache (if configured)
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') != 'ok':
                raise Exception('Cache set/get mismatch')
        except Exception as e:
            logger.warning(f'Cache health check failed: {str(e)}')
            # Don't mark as unhealthy, cache is optional

        return Response(health_status)
