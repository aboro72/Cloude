import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.mongo_audit import upsert_plugin_log
from plugins.models import PluginLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PluginLog)
def sync_plugin_log_to_mongo(sender, instance, **kwargs):
    try:
        upsert_plugin_log(instance)
    except Exception as exc:
        logger.warning("Mongo sync failed for PluginLog %s: %s", instance.pk, exc)
