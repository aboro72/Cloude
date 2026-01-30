"""
Custom permissions for API.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from sharing.models import UserShare, PublicLink


class IsFileOwnerOrShared(BasePermission):
    """
    Permission to check if user is file owner or has share access.
    """

    def has_object_permission(self, request, view, obj):
        """Check file permissions"""
        # Owner has all permissions
        if obj.owner == request.user:
            return True

        # Check if file is shared with user
        share = UserShare.objects.filter(
            shared_with=request.user,
            object_id=obj.id,
            is_active=True
        ).first()

        if not share:
            return False

        # Check permission level
        if request.method in SAFE_METHODS:
            return share.can_view()
        else:
            return share.can_edit()


class IsPublicLinkValid(BasePermission):
    """
    Permission to check if public link is valid and accessible.
    """

    def has_permission(self, request, view):
        """Check public link validity"""
        token = view.kwargs.get('token')

        try:
            link = PublicLink.objects.get(token=token, is_active=True)
        except PublicLink.DoesNotExist:
            return False

        # Check expiration
        if link.is_expired():
            return False

        return True


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission to allow only owners to edit their objects.
    """

    def has_object_permission(self, request, view, obj):
        """Check ownership"""
        if request.method in SAFE_METHODS:
            return True

        return obj.owner == request.user


class IsAdminUser(BasePermission):
    """
    Permission to check if user is admin.
    """

    def has_permission(self, request, view):
        """Check if user is admin"""
        return request.user and request.user.is_authenticated and request.user.is_staff
