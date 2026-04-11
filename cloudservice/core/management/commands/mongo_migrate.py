from django.core.management.base import BaseCommand, CommandError

from core.mongodb import is_available
from core.mongo_models import (
    MongoGroupShare,
    MongoPlugin,
    MongoPluginLog,
    MongoStorageFile,
    MongoStorageFolder,
    MongoTeamSiteNews,
    MongoUserProfile,
    upsert_document,
)
from accounts.models import UserProfile
from core.models import StorageFile, StorageFolder
from sharing.models import GroupShare, TeamSiteNews
from plugins.models import Plugin, PluginLog
from django.db import connection


class Command(BaseCommand):
    help = "Überträgt Relationaldaten komplett nach MongoDB."

    def handle(self, *args, **options):
        if not is_available():
            raise CommandError("MongoDB ist nicht verfügbar")

        self.stdout.write("Starte Migration zu MongoDB…")
        self._migrate_user_profiles()
        self._migrate_storage()
        self._migrate_group_shares()
        self._migrate_team_news()
        self._migrate_plugins()
        self.stdout.write(self.style.SUCCESS("MongoDB-Migration abgeschlossen."))

    def _migrate_user_profiles(self):
        for profile in UserProfile.objects.select_related('user', 'company', 'department_ref').iterator():
            doc = MongoUserProfile(
                user_id=profile.user_id,
                username=profile.user.username,
                email=profile.user.email or '',
                company_id=getattr(profile.company, 'id', None),
                department_id=getattr(profile.department_ref, 'id', None),
                role=profile.role,
                storage_quota=profile.storage_quota,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            upsert_document('user_profiles', doc)

    def _migrate_storage(self):
        for folder in StorageFolder.objects.iterator():
            doc = MongoStorageFolder(
                id=folder.id,
                owner_id=folder.owner_id,
                parent_id=folder.parent_id,
                name=folder.name,
                is_public=folder.is_public,
                is_starred=folder.is_starred,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
            )
            upsert_document('storage_folders', doc)

        for file in StorageFile.objects.iterator():
            doc = MongoStorageFile(
                id=file.id,
                owner_id=file.owner_id,
                folder_id=file.folder_id,
                name=file.name,
                size=file.size,
                mime_type=file.mime_type or '',
                file_hash=file.file_hash or '',
                version_count=file.version_count,
                created_at=file.created_at,
                updated_at=file.updated_at,
            )
            upsert_document('storage_files', doc)

    def _migrate_group_shares(self):
        for share in GroupShare.objects.iterator():
            doc = MongoGroupShare(
                id=share.id,
                group_name=share.group_name,
                owner_id=share.owner_id,
                company_id=share.company_id,
                department_id=share.department_id,
                created_at=share.created_at,
            )
            upsert_document('group_shares', doc)

    def _migrate_team_news(self):
        for news in TeamSiteNews.objects.iterator():
            doc = MongoTeamSiteNews(
                id=news.id,
                group_id=news.group_id,
                title=news.title,
                author_id=news.author_id,
                is_published=news.is_published,
                is_pinned=news.is_pinned,
                created_at=news.created_at,
            )
            upsert_document('team_news', doc)

    def _migrate_plugins(self):
        for plugin in Plugin.objects.iterator():
            doc = MongoPlugin(
                id=str(plugin.id),
                name=plugin.name,
                slug=plugin.slug,
                status=plugin.status,
                enabled=plugin.enabled,
                uploaded_at=plugin.uploaded_at,
            )
            upsert_document('plugins', doc)

        for log in PluginLog.objects.iterator():
            doc = MongoPluginLog(
                id=log.id,
                plugin_id=str(log.plugin_id),
                action=log.action,
                message=log.message,
                created_at=log.created_at,
            )
            upsert_document('plugin_logs', doc)
