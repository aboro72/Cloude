import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.mongo_audit import upsert_team_news
from sharing.models import TeamSiteNews

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TeamSiteNews)
def sync_team_news_to_mongo(sender, instance, **kwargs):
    try:
        upsert_team_news(instance)
    except Exception as exc:
        logger.warning("Mongo sync failed for TeamSiteNews %s: %s", instance.pk, exc)
