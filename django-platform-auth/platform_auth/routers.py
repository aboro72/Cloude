"""
Database router for directing platform_auth models to shared database.
"""


class PlatformAuthRouter:
    """
    Database router to direct platform_auth models to a specific database.
    Useful for keeping authentication data in a shared database while
    other app-specific data stays in separate databases.
    """

    def db_for_read(self, model, **hints):
        """
        Direct reads of platform_auth models to 'platform_auth_db'.
        """
        if model._meta.app_label == 'platform_auth':
            return 'platform_auth_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Direct writes of platform_auth models to 'platform_auth_db'.
        """
        if model._meta.app_label == 'platform_auth':
            return 'platform_auth_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between platform_auth models.
        """
        db1 = self.db_for_read(type(obj1), instance=obj1)
        db2 = self.db_for_read(type(obj2), instance=obj2)

        if db1 and db2:
            return db1 == db2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure platform_auth migrations happen on 'platform_auth_db'.
        """
        if app_label == 'platform_auth':
            return db == 'platform_auth_db'
        return None
