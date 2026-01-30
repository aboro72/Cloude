"""
Tests for CloudService models.
"""

import pytest
from django.contrib.auth.models import User
from core.models import StorageFile, StorageFolder, FileVersion
from accounts.models import UserProfile
from sharing.models import UserShare, PublicLink


@pytest.mark.django_db
class TestStorageFolder:
    """Tests for StorageFolder model"""

    def test_create_folder(self, user):
        """Test creating a folder"""
        folder = StorageFolder.objects.create(
            owner=user,
            name='Test Folder',
            description='Test description'
        )

        assert folder.name == 'Test Folder'
        assert folder.owner == user
        assert folder.parent is None

    def test_folder_path(self, user):
        """Test getting folder path"""
        parent = StorageFolder.objects.create(
            owner=user,
            name='Parent'
        )
        child = StorageFolder.objects.create(
            owner=user,
            name='Child',
            parent=parent
        )

        assert child.get_path() == '/Parent/Child'

    def test_subfolder_creation(self, user):
        """Test creating subfolders"""
        parent = StorageFolder.objects.create(
            owner=user,
            name='Parent'
        )
        child1 = StorageFolder.objects.create(
            owner=user,
            name='Child1',
            parent=parent
        )
        child2 = StorageFolder.objects.create(
            owner=user,
            name='Child2',
            parent=parent
        )

        assert parent.subfolders.count() == 2
        assert list(parent.subfolders.all()) == [child1, child2]


@pytest.mark.django_db
class TestStorageFile:
    """Tests for StorageFile model"""

    def test_create_file(self, user, folder, tmpfile):
        """Test creating a file"""
        file = StorageFile.objects.create(
            owner=user,
            folder=folder,
            name='test.txt',
            size=1024
        )

        assert file.name == 'test.txt'
        assert file.owner == user
        assert file.folder == folder

    def test_file_icon_class(self, user, folder):
        """Test getting file icon class"""
        files_icons = [
            ('document.pdf', 'bi-file-pdf'),
            ('image.jpg', 'bi-file-image'),
            ('video.mp4', 'bi-file-play'),
            ('audio.mp3', 'bi-file-music'),
            ('archive.zip', 'bi-file-zip'),
        ]

        for filename, expected_icon in files_icons:
            file = StorageFile.objects.create(
                owner=user,
                folder=folder,
                name=filename,
                size=1024
            )

            assert file.get_icon_class() == expected_icon

    def test_file_extension(self, user, folder):
        """Test getting file extension"""
        file = StorageFile.objects.create(
            owner=user,
            folder=folder,
            name='document.pdf',
            size=1024
        )

        assert file.get_extension() == 'pdf'

    def test_increment_download_count(self, user, folder):
        """Test incrementing download count"""
        file = StorageFile.objects.create(
            owner=user,
            folder=folder,
            name='test.txt',
            size=1024,
            download_count=0
        )

        assert file.download_count == 0

        file.increment_download_count()
        file.refresh_from_db()

        assert file.download_count == 1
        assert file.last_accessed is not None


@pytest.mark.django_db
class TestUserProfile:
    """Tests for UserProfile model"""

    def test_storage_quota_check(self, user):
        """Test storage quota checking"""
        profile = user.profile
        profile.storage_quota = 1024 * 1024  # 1 MB

        # Create files totaling 800KB
        folder = StorageFolder.objects.create(owner=user)
        StorageFile.objects.create(
            owner=user,
            folder=folder,
            name='file1.txt',
            size=400 * 1024
        )
        StorageFile.objects.create(
            owner=user,
            folder=folder,
            name='file2.txt',
            size=400 * 1024
        )

        # Should not be full
        assert not profile.is_storage_full()

        # Should trigger warning at 80%
        assert profile.is_storage_warning(threshold_percent=80)

    def test_storage_remaining(self, user):
        """Test calculating remaining storage"""
        profile = user.profile
        profile.storage_quota = 1024 * 1024 * 1024  # 1 GB
        profile.save()

        folder = StorageFolder.objects.create(owner=user)
        StorageFile.objects.create(
            owner=user,
            folder=folder,
            name='file.txt',
            size=100 * 1024 * 1024  # 100 MB
        )

        remaining = profile.get_storage_remaining()
        expected = (1024 * 1024 * 1024) - (100 * 1024 * 1024)

        assert remaining == expected


@pytest.mark.django_db
class TestUserShare:
    """Tests for UserShare model"""

    def test_create_share(self, user):
        """Test creating a user share"""
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com'
        )

        from django.contrib.contenttypes.models import ContentType

        folder = StorageFolder.objects.create(owner=user, name='Shared Folder')
        content_type = ContentType.objects.get_for_model(StorageFolder)

        share = UserShare.objects.create(
            owner=user,
            shared_with=user2,
            content_type=content_type,
            object_id=folder.id,
            permission='view'
        )

        assert share.owner == user
        assert share.shared_with == user2
        assert share.permission == 'view'

    def test_share_permissions(self, user):
        """Test checking share permissions"""
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com'
        )

        from django.contrib.contenttypes.models import ContentType

        folder = StorageFolder.objects.create(owner=user)
        content_type = ContentType.objects.get_for_model(StorageFolder)

        # View only
        share = UserShare.objects.create(
            owner=user,
            shared_with=user2,
            content_type=content_type,
            object_id=folder.id,
            permission='view'
        )

        assert share.can_view()
        assert not share.can_edit()
        assert not share.can_delete()

        # Edit permission
        share.permission = 'edit'
        share.save()

        assert share.can_view()
        assert share.can_edit()
        assert not share.can_delete()


@pytest.mark.django_db
class TestFileVersion:
    """Tests for FileVersion model"""

    def test_create_version(self, user, folder):
        """Test creating a file version"""
        file = StorageFile.objects.create(
            owner=user,
            folder=folder,
            name='test.txt',
            size=1024
        )

        version = FileVersion.objects.create(
            file=file,
            version_number=1,
            size=1024,
            file_hash='abc123',
            is_current=True
        )

        assert version.version_number == 1
        assert version.is_current
        assert str(version).startswith('test.txt')

    def test_version_history(self, user, folder):
        """Test version history"""
        file = StorageFile.objects.create(
            owner=user,
            folder=folder,
            name='test.txt',
            size=1024
        )

        # Create multiple versions
        for i in range(1, 4):
            FileVersion.objects.create(
                file=file,
                version_number=i,
                size=1024 * i,
                file_hash=f'hash{i}',
                is_current=(i == 3)
            )

        # Only latest should be current
        current_versions = FileVersion.objects.filter(
            file=file,
            is_current=True
        )

        assert current_versions.count() == 1
        assert current_versions.first().version_number == 3
