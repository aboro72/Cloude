"""
Dynamic template loader for plugins.

This loader scans the plugins/installed directory at runtime,
allowing newly installed plugins to have their templates found
without requiring a server restart.
"""

import os
from pathlib import Path
from django.template.loaders.filesystem import Loader as FilesystemLoader
from django.conf import settings


class PluginTemplateLoader(FilesystemLoader):
    """
    A template loader that dynamically discovers plugin template directories.

    Unlike the standard filesystem loader which only reads directories at startup,
    this loader scans the plugins/installed directory on each template lookup.
    """

    def get_dirs(self):
        """
        Dynamically return all plugin template directories.
        This is called for each template lookup, ensuring new plugins are found.
        """
        dirs = []

        # Get the plugins/installed directory
        plugins_dir = Path(settings.BASE_DIR) / 'plugins' / 'installed'

        if plugins_dir.exists():
            for plugin_dir in plugins_dir.iterdir():
                if plugin_dir.is_dir() and not plugin_dir.name.startswith('_'):
                    templates_dir = plugin_dir / 'templates'
                    if templates_dir.exists() and templates_dir.is_dir():
                        dirs.append(str(templates_dir))

        return dirs
