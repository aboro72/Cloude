from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict

from core.mongodb import get_collection, is_available


@dataclass
class MongoDocument:
    """Base helper for Mongo documents stored via `replace_one`."""

    def normalize(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MongoUserProfile(MongoDocument):
    user_id: int
    username: str
    email: str
    company_id: int | None
    department_id: int | None
    role: str
    storage_quota: int
    created_at: datetime
    updated_at: datetime


@dataclass
class MongoStorageFile(MongoDocument):
    id: int
    owner_id: int
    folder_id: int
    name: str
    size: int
    mime_type: str
    file_hash: str
    version_count: int
    created_at: datetime
    updated_at: datetime


@dataclass
class MongoStorageFolder(MongoDocument):
    id: int
    owner_id: int
    parent_id: int | None
    name: str
    is_public: bool
    is_starred: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class MongoGroupShare(MongoDocument):
    id: int
    group_name: str
    owner_id: int | None
    company_id: int | None
    department_id: int | None
    created_at: datetime


@dataclass
class MongoTeamSiteNews(MongoDocument):
    id: int
    group_id: int
    title: str
    author_id: int | None
    is_published: bool
    is_pinned: bool
    created_at: datetime


@dataclass
class MongoPlugin(MongoDocument):
    id: str
    name: str
    slug: str
    status: str
    enabled: bool
    uploaded_at: datetime


@dataclass
class MongoPluginLog(MongoDocument):
    id: int
    plugin_id: str
    action: str
    message: str
    created_at: datetime


def upsert_document(collection_name: str, document: MongoDocument):
    if not is_available():
        return False
    collection = get_collection(collection_name)
    if collection is None:
        return False
    data = document.normalize()
    collection.replace_one({'_id': data.get('id') or data.get('user_id') or data.get('source_id')}, data, upsert=True)
    return True
