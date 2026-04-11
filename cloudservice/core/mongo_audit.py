from dataclasses import dataclass

from core.mongodb import get_collection, is_available, mongo_write_enabled


ACTIVITY_TYPE_LABELS = {
    'upload': 'Upload',
    'download': 'Download',
    'delete': 'Delete',
    'rename': 'Rename',
    'move': 'Move',
    'share': 'Share',
    'unshare': 'Unshare',
    'view': 'View',
    'create_folder': 'Create Folder',
    'permission_change': 'Permission Change',
}



def _get_mongo_collection(collection_name, *, write=False):
    if write and not mongo_write_enabled(collection_name):
        return None
    return get_collection(collection_name)


@dataclass
class MongoActivityLogEntry:
    id: int
    user_id: int
    activity_type: str
    description: str
    created_at: object
    file_id: int | None = None
    file_name: str = ''
    folder_id: int | None = None
    folder_name: str = ''
    ip_address: str = ''
    user_agent: str = ''

    @property
    def file(self):
        if not self.file_id:
            return None
        return type('MongoFileRef', (), {'id': self.file_id, 'name': self.file_name})()

    @property
    def folder(self):
        if not self.folder_id:
            return None
        return type('MongoFolderRef', (), {'id': self.folder_id, 'name': self.folder_name})()

    @property
    def get_activity_type_display(self):
        return ACTIVITY_TYPE_LABELS.get(self.activity_type, self.activity_type)


@dataclass
class MongoPluginLogEntry:
    id: int
    plugin_id: str
    plugin_name: str
    action: str
    message: str
    created_at: object
    user_id: int | None = None
    username: str = ''

    @property
    def plugin(self):
        return type('MongoPluginRef', (), {'id': self.plugin_id, 'name': self.plugin_name})()

    @property
    def user(self):
        if not self.user_id:
            return None
        return type('MongoUserRef', (), {'id': self.user_id, 'username': self.username})()


def _normalize_company_id(instance):
    user = getattr(instance, 'user', None)
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'company_id', None)


def build_activity_log_document(instance):
    return {
        '_id': f'activity:{instance.pk}',
        'source_id': instance.pk,
        'user_id': instance.user_id,
        'username': instance.user.username,
        'company_id': _normalize_company_id(instance),
        'activity_type': instance.activity_type,
        'description': instance.description,
        'file_id': instance.file_id,
        'file_name': instance.file.name if instance.file_id and instance.file else '',
        'folder_id': instance.folder_id,
        'folder_name': instance.folder.name if instance.folder_id and instance.folder else '',
        'ip_address': instance.ip_address or '',
        'user_agent': instance.user_agent or '',
        'created_at': instance.created_at,
        'updated_at': instance.updated_at,
    }


def build_notification_document(instance):
    return {
        '_id': f'notification:{instance.pk}',
        'source_id': instance.pk,
        'user_id': instance.user_id,
        'username': instance.user.username,
        'company_id': getattr(getattr(instance.user, 'profile', None), 'company_id', None),
        'notification_type': instance.notification_type,
        'title': instance.title,
        'message': instance.message,
        'url': instance.url,
        'is_read': instance.is_read,
        'created_at': instance.created_at,
        'expires_at': instance.expires_at,
    }


def build_audit_log_document(instance):
    return {
        '_id': f'audit:{instance.pk}',
        'source_id': instance.pk,
        'user_id': instance.user_id,
        'username': instance.user.username,
        'company_id': getattr(getattr(instance.user, 'profile', None), 'company_id', None),
        'action': instance.action,
        'description': instance.description,
        'ip_address': instance.ip_address or '',
        'user_agent': instance.user_agent or '',
        'created_at': instance.created_at,
    }


def build_team_news_document(instance):
    company = instance.group.company if instance.group_id and instance.group and instance.group.company_id else None
    department = instance.group.department if instance.group_id and instance.group and instance.group.department_id else None
    return {
        '_id': f'team_news:{instance.pk}',
        'source_id': instance.pk,
        'group_id': instance.group_id,
        'group_name': instance.group.group_name if instance.group_id and instance.group else '',
        'company_id': company.id if company else None,
        'company_slug': company.slug if company else '',
        'department_id': department.id if department else None,
        'department_name': department.name if department else '',
        'author_id': instance.author_id,
        'author_username': instance.author.username if instance.author_id and instance.author else '',
        'title': instance.title,
        'category': instance.category,
        'summary': instance.summary,
        'content': instance.content,
        'tags': instance.tags,
        'is_published': instance.is_published,
        'is_pinned': instance.is_pinned,
        'publish_at': instance.publish_at,
        'view_count': instance.view_count,
        'created_at': instance.created_at,
        'updated_at': instance.updated_at,
    }


def build_plugin_log_document(instance):
    return {
        '_id': f'plugin_log:{instance.pk}',
        'source_id': instance.pk,
        'plugin_id': str(instance.plugin_id),
        'plugin_name': instance.plugin.name,
        'plugin_slug': instance.plugin.slug,
        'action': instance.action,
        'message': instance.message,
        'user_id': instance.user_id,
        'username': instance.user.username if instance.user_id and instance.user else '',
        'created_at': instance.created_at,
    }


def upsert_activity_log(instance):
    collection = _get_mongo_collection('activity_logs', write=True)
    if collection is None:
        return False
    document = build_activity_log_document(instance)
    collection.replace_one({'_id': document['_id']}, document, upsert=True)
    return True


def upsert_notification(instance):
    collection = _get_mongo_collection('notifications', write=True)
    if collection is None:
        return False
    document = build_notification_document(instance)
    collection.replace_one({'_id': document['_id']}, document, upsert=True)
    return True


def upsert_audit_log(instance):
    collection = _get_mongo_collection('account_audit_logs', write=True)
    if collection is None:
        return False
    document = build_audit_log_document(instance)
    collection.replace_one({'_id': document['_id']}, document, upsert=True)
    return True


def upsert_team_news(instance):
    collection = _get_mongo_collection('team_news', write=True)
    if collection is None:
        return False
    document = build_team_news_document(instance)
    collection.replace_one({'_id': document['_id']}, document, upsert=True)
    return True


def upsert_plugin_log(instance):
    collection = _get_mongo_collection('plugin_logs', write=True)
    if collection is None:
        return False
    document = build_plugin_log_document(instance)
    collection.replace_one({'_id': document['_id']}, document, upsert=True)
    return True


def log_search_event(*, user=None, query='', source='web', results=None):
    collection = _get_mongo_collection('search_events', write=True)
    if collection is None:
        return False
    profile = getattr(user, 'profile', None) if user else None
    company = getattr(profile, 'company', None) if profile else None
    collection.insert_one({
        'user_id': getattr(user, 'id', None),
        'username': getattr(user, 'username', ''),
        'company_id': getattr(company, 'id', None),
        'company_slug': getattr(company, 'slug', ''),
        'query': query,
        'source': source,
        'results': results or {},
    })
    return True


def get_user_activity_entries(user, limit=200):
    if not is_available():
        return []
    collection = _get_mongo_collection('activity_logs')
    if collection is None:
        return []
    rows = collection.find({'user_id': user.id}).sort('created_at', -1).limit(limit)
    return [
        MongoActivityLogEntry(
            id=row.get('source_id'),
            user_id=row.get('user_id'),
            activity_type=row.get('activity_type', ''),
            description=row.get('description', ''),
            created_at=row.get('created_at'),
            file_id=row.get('file_id'),
            file_name=row.get('file_name', ''),
            folder_id=row.get('folder_id'),
            folder_name=row.get('folder_name', ''),
            ip_address=row.get('ip_address', ''),
            user_agent=row.get('user_agent', ''),
        )
        for row in rows
    ]


def get_plugin_log_entries(limit=50):
    if not is_available():
        return []
    collection = _get_mongo_collection('plugin_logs')
    if collection is None:
        return []
    rows = collection.find().sort('created_at', -1).limit(limit)
    return [
        MongoPluginLogEntry(
            id=row.get('source_id'),
            plugin_id=row.get('plugin_id', ''),
            plugin_name=row.get('plugin_name', ''),
            action=row.get('action', ''),
            message=row.get('message', ''),
            created_at=row.get('created_at'),
            user_id=row.get('user_id'),
            username=row.get('username', ''),
        )
        for row in rows
    ]
