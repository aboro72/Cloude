"""
Pytest configuration and fixtures.
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pytest
from django.contrib.auth.models import User
from core.models import StorageFile, StorageFolder
from accounts.models import UserProfile
from factory import DjangoModelFactory, Faker
from factory.django import DjangoOptions


class UserFactory(DjangoModelFactory):
    """Factory for creating test users"""
    class Meta:
        model = User

    username = Faker('user_name')
    email = Faker('email')
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    is_active = True

    @staticmethod
    def _create(model_class, *args, **kwargs):
        """Override to use set_password for password"""
        obj = model_class(*args, **kwargs)
        obj.set_password('testpass123')
        obj.save()
        return obj


class StorageFolderFactory(DjangoModelFactory):
    """Factory for creating test folders"""
    class Meta:
        model = StorageFolder

    name = Faker('word')
    owner = None  # Set by test
    parent = None
    description = Faker('text', max_nb_chars=100)
    is_public = False


class StorageFileFactory(DjangoModelFactory):
    """Factory for creating test files"""
    class Meta:
        model = StorageFile

    name = Faker('file_name')
    owner = None  # Set by test
    folder = None  # Set by test
    size = Faker('random_int', min=1024, max=1048576)  # 1KB - 1MB
    mime_type = 'text/plain'
    description = Faker('text', max_nb_chars=100)


@pytest.fixture
def user():
    """Create a test user"""
    return UserFactory()


@pytest.fixture
def admin_user():
    """Create an admin user"""
    user = UserFactory(is_staff=True, is_superuser=True)
    user.profile.role = 'admin'
    user.profile.save()
    return user


@pytest.fixture
def folder(user):
    """Create a test folder"""
    return StorageFolderFactory(owner=user)


@pytest.fixture
def file(user, folder):
    """Create a test file"""
    return StorageFileFactory(owner=user, folder=folder)


@pytest.fixture
def client():
    """Create a test client"""
    from django.test import Client
    return Client()


@pytest.fixture
def api_client():
    """Create a test API client"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated API client"""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client
