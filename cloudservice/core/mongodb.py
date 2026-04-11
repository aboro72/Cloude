"""
MongoDB connection utility for CloudService.

Vollständig optional — wenn MongoDB nicht erreichbar oder MONGODB_ENABLED=False,
liefern alle Funktionen None zurück und die App läuft normal mit SQLite/PostgreSQL.

Verwendung:
    from core.mongodb import get_db, get_collection, is_available

    if is_available():
        col = get_collection('my_collection')
        col.insert_one({'key': 'value'})
"""

import logging
import threading
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client = None
_available = None   # None = noch nicht geprüft, True/False = Ergebnis


def _build_uri() -> str:
    from django.conf import settings
    from urllib.parse import quote_plus

    explicit_uri = getattr(settings, 'MONGODB_URI', '')
    if explicit_uri:
        return explicit_uri

    user = getattr(settings, 'MONGODB_USER', '')
    password = getattr(settings, 'MONGODB_PASSWORD', '')
    host = getattr(settings, 'MONGODB_HOST', 'localhost')
    port = getattr(settings, 'MONGODB_PORT', 27017)
    auth_source = getattr(settings, 'MONGODB_AUTH_SOURCE', 'appdb')

    if user and password:
        return (
            f"mongodb://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/?authSource={auth_source}"
        )
    return f"mongodb://{host}:{port}/"


def _configure_dns_resolver():
    """Configure dnspython for mongodb+srv lookups when explicit resolvers are set."""
    from django.conf import settings

    uri = _build_uri()
    if not uri.startswith('mongodb+srv://'):
        return None

    nameservers = [
        item.strip()
        for item in str(getattr(settings, 'MONGODB_DNS_NAMESERVERS', '')).split(',')
        if item.strip()
    ]
    lifetime_ms = int(getattr(settings, 'MONGODB_DNS_LIFETIME_MS', 0) or 0)
    timeout_ms = int(getattr(settings, 'MONGODB_DNS_TIMEOUT_MS', 0) or 0)

    if not nameservers and not lifetime_ms and not timeout_ms:
        return None

    try:
        import dns.resolver
    except Exception as exc:
        logger.warning("MongoDB DNS override requested, but dnspython is unavailable: %s", exc)
        return None

    resolver = dns.resolver.Resolver(configure=not bool(nameservers))
    if nameservers:
        resolver.nameservers = nameservers
    if timeout_ms:
        resolver.timeout = max(timeout_ms / 1000.0, 1.0)
    if lifetime_ms:
        resolver.lifetime = max(lifetime_ms / 1000.0, resolver.timeout if timeout_ms else 1.0)
    dns.resolver.default_resolver = resolver
    return resolver


def _describe_client(client, db_name: str) -> str:
    """Return a compact description of the actual connected MongoDB deployment."""
    try:
        nodes = sorted(f"{host}:{port}" for host, port in (client.nodes or []))
        if nodes:
            return f"{','.join(nodes)}/{db_name}"
    except Exception:
        pass

    parsed = urlparse(_build_uri())
    if parsed.scheme == 'mongodb+srv':
        return f"{parsed.hostname}/{db_name}"
    if parsed.hostname:
        port = parsed.port or 27017
        return f"{parsed.hostname}:{port}/{db_name}"
    return db_name


def _init_client():
    """Verbindung aufbauen. Gibt None zurück wenn fehlgeschlagen."""
    global _client, _available
    from django.conf import settings
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

    if not getattr(settings, 'MONGODB_ENABLED', False):
        _available = False
        return None

    try:
        _configure_dns_resolver()
        client = MongoClient(
            _build_uri(),
            connectTimeoutMS=getattr(settings, 'MONGODB_CONNECT_TIMEOUT_MS', 3000),
            serverSelectionTimeoutMS=getattr(settings, 'MONGODB_SERVER_SELECTION_TIMEOUT_MS', 3000),
        )
        client[settings.MONGODB_DB].command('ping')
        _client = client
        _available = True
        logger.info("MongoDB verbunden -> %s", _describe_client(client, settings.MONGODB_DB))
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as exc:
        _client = None
        _available = False
        logger.warning("MongoDB nicht verfügbar – Fallback auf SQLite: %s", exc)

    return _client


def get_client():
    """Gibt den MongoClient zurück oder None wenn nicht verfügbar."""
    global _client, _available
    if _available is None:
        with _lock:
            if _available is None:
                _init_client()
    return _client


def is_available() -> bool:
    """True wenn MongoDB verbunden und nutzbar."""
    get_client()
    return bool(_available)


def get_db(db_name: str = None):
    """
    Gibt ein pymongo-Database-Objekt zurück oder None.

    Beispiel:
        db = get_db()
        if db is not None:
            db['logs'].insert_one({...})
    """
    client = get_client()
    if client is None:
        return None
    from django.conf import settings
    name = db_name or getattr(settings, 'MONGODB_DB', 'appdb')
    return client[name]




def resolve_collection_name(collection_name: str) -> str:
    from django.conf import settings

    prefix = str(getattr(settings, 'MONGODB_COLLECTION_PREFIX', '') or '').strip()
    if not prefix:
        return collection_name
    return f"{prefix}{collection_name}"


def mongo_write_enabled(collection_name: str) -> bool:
    from django.conf import settings

    raw = str(getattr(settings, 'MONGODB_WRITE_COLLECTIONS', '') or '')
    allowed = {item.strip() for item in raw.split(',') if item.strip()}
    if not allowed:
        return False
    return collection_name in allowed


def get_collection(collection_name: str, db_name: str = None):
    """
    Gibt eine pymongo-Collection zurück oder None.

    Beispiel:
        col = get_collection('events')
        if col is not None:
            col.insert_one({'action': 'login', 'user': username})
    """
    db = get_db(db_name)
    if db is None:
        return None
    return db[resolve_collection_name(collection_name)]


def ping() -> dict:
    """Verbindungstest. Gibt {'ok': True/False, 'info': str} zurück."""
    if not is_available():
        return {'ok': False, 'info': 'MongoDB nicht aktiviert oder nicht erreichbar (Fallback: SQLite)'}
    try:
        from django.conf import settings
        client = get_client()
        get_db().command('ping')
        return {'ok': True, 'info': f"MongoDB OK -> {_describe_client(client, settings.MONGODB_DB)}"}
    except Exception as exc:
        return {'ok': False, 'info': str(exc)}
