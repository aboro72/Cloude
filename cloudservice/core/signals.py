"""
Django signals for Core app.
Handles automatic tasks on model changes.
"""

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from core.models import StorageFile, StorageFolder, FileVersion, ActivityLog, Notification
from core.mongo_audit import upsert_activity_log, upsert_notification
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


# ---------------------------------------------------------------------------
# Notification Signals
# ---------------------------------------------------------------------------

def _notify_article_author_on_comment(comment):
    """Autor eines News-Artikels benachrichtigen, wenn jemand kommentiert."""
    try:
        from news.models import NewsArticle
        from django.contrib.contenttypes.models import ContentType
        from core.models import Notification

        ct = ContentType.objects.get_for_model(NewsArticle)
        if comment.content_type_id != ct.id:
            return  # Kein NewsArticle-Kommentar

        article = NewsArticle.objects.filter(pk=comment.object_id).first()
        if not article or not article.author:
            return
        if article.author == comment.author:
            return  # Kein Self-Notify

        Notification.notify(
            user=article.author,
            notification_type='comment',
            title=f'{comment.author.get_full_name() or comment.author.username} hat kommentiert',
            message=f'Auf deinen Artikel „{article.title}"',
            url=f'/news/{article.slug}/',
        )
    except Exception as e:
        logger.warning(f"Notification signal error (comment): {e}")


def _notify_on_published_article(article):
    """Alle aktiven User benachrichtigen wenn ein Artikel veröffentlicht wird."""
    try:
        from core.models import Notification
        from django.contrib.auth.models import User

        users = User.objects.filter(is_active=True).exclude(pk=article.author_id if article.author else 0)
        notifications = [
            Notification(
                user=u,
                notification_type='news',
                title=f'Neuer Artikel: {article.title}',
                message=article.summary[:120] if article.summary else '',
                url=f'/news/{article.slug}/',
            )
            for u in users
        ]
        Notification.objects.bulk_create(notifications, ignore_conflicts=True)
    except Exception as e:
        logger.warning(f"Notification signal error (news publish): {e}")


try:
    from news.models import Comment as NewsComment, NewsArticle

    @receiver(post_save, sender=NewsComment)
    def on_news_comment(sender, instance, created, **kwargs):
        if created:
            _notify_article_author_on_comment(instance)

    _prev_published = {}

    @receiver(post_save, sender=NewsArticle)
    def on_news_article_save(sender, instance, created, **kwargs):
        # Nur bei erstmaligem Veröffentlichen benachrichtigen
        if instance.is_published:
            prev = _prev_published.get(instance.pk)
            if not prev:
                _notify_on_published_article(instance)
        _prev_published[instance.pk] = instance.is_published

except Exception:
    pass  # news-App evtl. noch nicht geladen


@receiver(post_save, sender=ActivityLog)
def sync_activity_log_to_mongo(sender, instance, **kwargs):
    try:
        upsert_activity_log(instance)
    except Exception as exc:
        logger.warning("Mongo sync failed for ActivityLog %s: %s", instance.pk, exc)


@receiver(post_save, sender=Notification)
def sync_notification_to_mongo(sender, instance, **kwargs):
    try:
        upsert_notification(instance)
    except Exception as exc:
        logger.warning("Mongo sync failed for Notification %s: %s", instance.pk, exc)
