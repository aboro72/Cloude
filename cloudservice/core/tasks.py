"""
Celery tasks for background processing.
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from core.models import StorageFile, StorageFolder, ActivityLog, Notification
from accounts.models import UserProfile
from storage.models import StorageStats, StorageQuotaAlert, TrashBin
import logging

logger = logging.getLogger(__name__)


@shared_task(name='cleanup_trash', bind=True)
def cleanup_trash(self):
    """
    Delete trash items that have expired.
    Runs automatically via Celery Beat.
    """
    expired_items = TrashBin.objects.filter(expires_at__lt=timezone.now())
    count = expired_items.count()

    for item in expired_items:
        try:
            item.delete()
        except Exception as e:
            logger.error(f"Error deleting trash item {item.id}: {str(e)}")

    logger.info(f"Cleaned up {count} expired trash items")
    return f"Deleted {count} expired items"


@shared_task(name='update_storage_stats', bind=True)
def update_storage_stats(self):
    """
    Update cached storage statistics for all users.
    Runs periodically via Celery Beat.
    """
    users = User.objects.all()
    updated_count = 0

    for user in users:
        try:
            stats, _ = StorageStats.objects.get_or_create(user=user)

            # Calculate statistics
            files = StorageFile.objects.filter(owner=user)
            folders = StorageFolder.objects.filter(owner=user)

            stats.total_files = files.count()
            stats.total_folders = folders.count()
            stats.total_size = files.aggregate(
                total_size=models.Sum('size')
            )['total_size'] or 0

            from core.models import FileVersion
            stats.total_versions = FileVersion.objects.filter(
                file__owner=user
            ).count()

            stats.save()
            updated_count += 1

        except Exception as e:
            logger.error(f"Error updating stats for user {user.username}: {str(e)}")

    logger.info(f"Updated statistics for {updated_count} users")
    return f"Updated {updated_count} users"


@shared_task(name='check_storage_quota', bind=True)
def check_storage_quota(self):
    """
    Check user storage quotas and create alerts.
    Runs periodically via Celery Beat.
    """
    profiles = UserProfile.objects.filter(is_active=True)
    alerts_created = 0

    for profile in profiles:
        try:
            used_percentage = profile.get_storage_used_percentage()

            # Check for alerts
            if used_percentage >= 95:
                # Critical alert
                alert_type = 'critical'
            elif used_percentage >= 80:
                # Warning alert
                alert_type = 'warning'
            else:
                continue

            # Create alert if not already exists
            existing_alert = StorageQuotaAlert.objects.filter(
                user=profile.user,
                alert_type=alert_type,
                is_acknowledged=False
            ).exists()

            if not existing_alert:
                StorageQuotaAlert.objects.create(
                    user=profile.user,
                    alert_type=alert_type,
                    usage_percent=int(used_percentage)
                )
                alerts_created += 1

                # Send notification
                Notification.create_notification(
                    user=profile.user,
                    notification_type='storage_limit',
                    title='Storage Quota Alert',
                    message=f'Your storage usage is at {used_percentage:.1f}%',
                    expires_hours=72
                )

        except Exception as e:
            logger.error(f"Error checking quota for user {profile.user.username}: {str(e)}")

    logger.info(f"Created {alerts_created} storage quota alerts")
    return f"Created {alerts_created} alerts"


@shared_task(name='send_activity_digest', bind=True)
def send_activity_digest(self):
    """
    Send activity digest email to users.
    Runs daily via Celery Beat.
    """
    yesterday = timezone.now() - timezone.timedelta(days=1)
    users = User.objects.filter(profile__is_active=True)
    sent_count = 0

    for user in users:
        try:
            # Get activities from last 24 hours
            activities = ActivityLog.objects.filter(
                user=user,
                created_at__gte=yesterday
            )

            if not activities.exists():
                continue

            # Prepare email
            subject = "Your Daily Activity Digest"
            activity_list = "\n".join([
                f"- {a.get_activity_type_display()}: {a.description}"
                for a in activities[:10]
            ])

            message = f"""
Hello {user.get_full_name() or user.username},

Here's a summary of your CloudService activities from the last 24 hours:

{activity_list}

Log in to view more details: {settings.SITE_URL}

Best regards,
CloudService Team
            """

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=True
            )
            sent_count += 1

        except Exception as e:
            logger.error(f"Error sending digest to {user.username}: {str(e)}")

    logger.info(f"Sent activity digests to {sent_count} users")
    return f"Sent {sent_count} digests"


@shared_task(name='cleanup_old_versions', bind=True)
def cleanup_old_versions(self, days=30):
    """
    Delete old file versions.
    Configurable retention period.
    """
    from core.models import FileVersion

    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    old_versions = FileVersion.objects.filter(
        created_at__lt=cutoff_date,
        is_current=False
    )

    count = old_versions.count()
    old_versions.delete()

    logger.info(f"Deleted {count} file versions older than {days} days")
    return f"Deleted {count} versions"


@shared_task(name='generate_backup', bind=True)
def generate_backup(self, user_id):
    """
    Generate backup of user's files.
    """
    from storage.models import StorageBackup
    import tarfile
    import os

    try:
        user = User.objects.get(id=user_id)
        backup = StorageBackup.objects.create(user=user)

        # Create tar archive
        backup_path = f"/tmp/backup_{user_id}_{backup.id}.tar.gz"

        with tarfile.open(backup_path, "w:gz") as tar:
            files = StorageFile.objects.filter(owner=user)

            for file in files:
                try:
                    tar.add(file.file.path)
                    backup.backed_up_files += 1
                except Exception as e:
                    logger.error(f"Error backing up file {file.id}: {str(e)}")

        backup.total_files = files.count()
        backup.status = 'completed'
        backup.completed_at = timezone.now()
        backup.save()

        # Upload to storage
        # TODO: Implement S3/Cloud Storage upload

        logger.info(f"Backup completed for user {user.username}")
        return f"Backup created: {backup.id}"

    except Exception as e:
        backup.status = 'failed'
        backup.error_message = str(e)
        backup.completed_at = timezone.now()
        backup.save()

        logger.error(f"Error generating backup for user {user_id}: {str(e)}")
        return f"Backup failed: {str(e)}"


@shared_task(name='send_email', bind=True)
def send_email(self, subject, message, recipient_list, fail_silently=False):
    """
    Generic email sending task.
    """
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            recipient_list,
            fail_silently=fail_silently
        )
        logger.info(f"Email sent to {recipient_list}")
        return f"Email sent to {len(recipient_list)} recipients"
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return f"Error: {str(e)}"


@shared_task(name='cleanup_expired_notifications', bind=True)
def cleanup_expired_notifications(self):
    """
    Delete expired notifications.
    """
    expired = Notification.objects.filter(expires_at__lt=timezone.now())
    count = expired.count()
    expired.delete()

    logger.info(f"Deleted {count} expired notifications")
    return f"Deleted {count} notifications"


# Import models at the end to avoid circular imports
from django.db import models
