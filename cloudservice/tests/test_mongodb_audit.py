from datetime import datetime

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from api.serializers import ActivityLogSerializer
from core.models import ActivityLog
from core.mongo_audit import (
    MongoActivityLogEntry,
    MongoPluginLogEntry,
    build_activity_log_document,
    build_plugin_log_document,
    build_team_news_document,
    get_user_activity_entries,
)
from plugins.models import Plugin, PluginLog
from sharing.models import GroupShare, TeamSiteNews
from django.contrib.contenttypes.models import ContentType
from core.models import StorageFolder


class MongoAuditTests(TestCase):
    def test_build_activity_log_document_contains_company_context(self):
        user = User.objects.create_user(username='mongo-audit', password='secret123')
        activity = ActivityLog.objects.create(
            user=user,
            activity_type='upload',
            description='Uploaded file',
        )

        document = build_activity_log_document(activity)

        self.assertEqual(document['source_id'], activity.id)
        self.assertEqual(document['user_id'], user.id)
        self.assertEqual(document['activity_type'], 'upload')
        self.assertIsNone(document['company_id'])

    def test_activity_serializer_handles_mongo_entries(self):
        entry = MongoActivityLogEntry(
            id=7,
            user_id=3,
            activity_type='upload',
            description='Uploaded report.pdf',
            created_at=datetime(2026, 4, 10, 18, 45),
            file_id=9,
            file_name='report.pdf',
        )

        data = ActivityLogSerializer(entry).data

        self.assertEqual(data['id'], 7)
        self.assertEqual(data['user'], 3)
        self.assertEqual(data['user_username'], '')
        self.assertEqual(data['activity_type_display'], 'Upload')
        self.assertEqual(data['file'], 9)
        self.assertIsNone(data['folder'])

    @override_settings(MONGODB_ENABLED=False)
    def test_get_user_activity_entries_returns_empty_when_mongo_disabled(self):
        user = User.objects.create_user(username='mongo-disabled', password='secret123')
        self.assertEqual(get_user_activity_entries(user), [])

    def test_build_team_news_document_contains_company_slug(self):
        owner = User.objects.create_user(username='teamnews-owner', password='secret123')
        company = owner.profile.company
        if company is None:
            from departments.models import Company
            company = Company.objects.create(name='Mongo Team GmbH', owner=owner)
            company.admins.add(owner)
            owner.profile.company = company
            owner.profile.save(update_fields=['company'])
        library = StorageFolder.objects.create(owner=owner, parent=None, name='Team Library')
        group = GroupShare.objects.create(
            owner=owner,
            company=company,
            group_name='Team Mongo',
            content_type=ContentType.objects.get_for_model(StorageFolder),
            object_id=library.id,
            permission='admin',
        )
        news = TeamSiteNews.objects.create(group=group, title='Mongo News', author=owner, content='hello')

        document = build_team_news_document(news)

        self.assertEqual(document['group_id'], group.id)
        self.assertEqual(document['company_slug'], company.slug)
        self.assertEqual(document['author_username'], owner.username)

    def test_build_plugin_log_document_contains_plugin_context(self):
        user = User.objects.create_user(username='plugin-admin', password='secret123')
        plugin = Plugin.objects.create(
            name='Mongo Plugin',
            slug='mongo-plugin',
            version='1.0.0',
            author='Codex',
            description='Test plugin',
        )
        log = PluginLog.objects.create(plugin=plugin, action='uploaded', user=user, message='Uploaded')

        document = build_plugin_log_document(log)

        self.assertEqual(document['plugin_slug'], 'mongo-plugin')
        self.assertEqual(document['username'], user.username)

    def test_mongo_plugin_log_entry_exposes_template_like_properties(self):
        entry = MongoPluginLogEntry(
            id=4,
            plugin_id='plugin-1',
            plugin_name='Plugin One',
            action='uploaded',
            message='Uploaded',
            created_at=datetime(2026, 4, 10, 19, 0),
            user_id=11,
            username='admin',
        )

        self.assertEqual(entry.plugin.name, 'Plugin One')
        self.assertEqual(entry.user.username, 'admin')
