from django.db import models
from django.utils.translation import gettext_lazy as _


class UserQuerySet(models.QuerySet):
    """Custom queryset for User model"""

    def admins(self):
        """Return all admin users"""
        return self.filter(role='admin')

    def support_agents(self):
        """Return all support agents"""
        return self.filter(role='support_agent')

    def customers(self):
        """Return all customers"""
        return self.filter(role='customer')

    def active(self):
        """Return all active users"""
        return self.filter(is_active=True)

    def inactive(self):
        """Return all inactive users"""
        return self.filter(is_active=False)

    def with_email_verified(self):
        """Return users with verified email"""
        return self.filter(email_verified=True)

    def with_2fa(self):
        """Return users with 2FA enabled"""
        return self.filter(is_two_factor_enabled=True)


class UserManager(models.Manager):
    """Custom manager for User model"""

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def admins(self):
        """Get all admin users"""
        return self.get_queryset().admins()

    def support_agents(self):
        """Get all support agents"""
        return self.get_queryset().support_agents()

    def customers(self):
        """Get all customers"""
        return self.get_queryset().customers()

    def active(self):
        """Get all active users"""
        return self.get_queryset().active()

    def create_user(self, email, username, password=None, **extra_fields):
        """Create a regular user"""
        from .models import User
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, username, password, **extra_fields)
