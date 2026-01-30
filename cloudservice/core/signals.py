"""
Django signals for Core app.
Handles automatic tasks on model changes.
"""

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from core.models import StorageFile, StorageFolder, FileVersion, ActivityLog
import os
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StorageFile)
def create_initial_file_version(sender, instance, created, **kwargs):
    """
    Create initial version entry when file is uploaded.
    """
    if created and instance.file:
        FileVersion.objects.create(
            file=instance,
            version_number=1,
            file_data=instance.file,
            file_hash=instance.file_hash,
            size=instance.size,
            is_current=True
        )
        logger.info(f"Created initial version for file: {instance.name}")


@receiver(pre_delete, sender=StorageFile)
def delete_file_on_disk(sender, instance, **kwargs):
    """
    Delete file from disk when StorageFile is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            try:
                os.remove(instance.file.path)
                logger.info(f"Deleted file from disk: {instance.file.path}")
            except Exception as e:
                logger.error(f"Error deleting file {instance.file.path}: {str(e)}")

    # Delete all versions
    for version in instance.versions.all():
        if version.file_data:
            if os.path.isfile(version.file_data.path):
                try:
                    os.remove(version.file_data.path)
                except Exception as e:
                    logger.error(f"Error deleting version file: {str(e)}")


@receiver(post_delete, sender=StorageFolder)
def delete_folder_contents(sender, instance, **kwargs):
    """
    Cascade delete files and subfolders.
    Note: Django handles this via CASCADE, but this signal can be used for logging.
    """
    logger.info(f"Folder deleted: {instance.name} (Owner: {instance.owner.username})")


@receiver(post_save, sender=User)
def create_user_root_folder(sender, instance, created, **kwargs):
    """
    Create root folder for new user.
    """
    if created:
        try:
            StorageFolder.objects.create(
                owner=instance,
                parent=None,
                name='Cloud',
                description=f"Root folder for {instance.username}"
            )
            logger.info(f"Created root folder for user: {instance.username}")
        except Exception as e:
            logger.error(f"Error creating root folder for user {instance.username}: {str(e)}")
