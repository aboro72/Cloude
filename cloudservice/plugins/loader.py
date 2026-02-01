"""
Plugin loader and lifecycle management.

Handles ZIP validation, extraction, dynamic loading/unloading of plugins,
folder-based plugin discovery, and hot-loading (activation/deactivation
without server restart).
"""

import os
import sys
import json
import zipfile
import shutil
import importlib
from pathlib import Path
from typing import Dict, Any, Optional, List

from django.conf import settings
from django.apps import apps
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Handles all plugin loading, validation, and lifecycle operations.

    Supports:
    - ZIP file validation and extraction
    - Dynamic plugin importing
    - Runtime INSTALLED_APPS modification
    - Hot-loading (activate/deactivate without restart)
    - Error handling and recovery
    """

    PLUGINS_DIR = Path(settings.BASE_DIR) / 'plugins' / 'installed'

    def __init__(self):
        """Initialize plugin loader and create plugins directory"""
        self.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"PluginLoader initialized with PLUGINS_DIR: {self.PLUGINS_DIR}")

    def discover_plugins(self) -> List[Dict[str, Any]]:
        """
        Discover plugins from folder structure in PLUGINS_DIR.

        Scans for folders containing plugin.json and registers them
        in the database if not already present.

        Returns:
            List of discovered plugin manifests
        """
        from plugins.models import Plugin, PluginLog

        discovered = []
        logger.info(f"Discovering plugins in {self.PLUGINS_DIR}")

        if not self.PLUGINS_DIR.exists():
            logger.warning(f"Plugins directory does not exist: {self.PLUGINS_DIR}")
            return discovered

        for item in self.PLUGINS_DIR.iterdir():
            if not item.is_dir():
                continue

            # Skip __pycache__ and hidden folders
            if item.name.startswith('_') or item.name.startswith('.'):
                continue

            manifest_path = item / 'plugin.json'
            if not manifest_path.exists():
                logger.debug(f"Skipping {item.name}: no plugin.json found")
                continue

            try:
                # Parse manifest
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

                # Validate required fields
                required_fields = ['name', 'slug', 'version']
                missing = [f for f in required_fields if f not in manifest]
                if missing:
                    logger.warning(f"Plugin {item.name} missing fields: {missing}")
                    continue

                # Check if plugin already exists in database
                slug = manifest['slug']
                module_name = slug.replace('-', '_')

                # Extract settings schema if present
                settings_config = manifest.get('settings', {})
                has_settings = settings_config.get('has_settings', False)
                settings_schema = settings_config.get('schema', {})

                plugin, created = Plugin.objects.get_or_create(
                    slug=slug,
                    defaults={
                        'name': manifest['name'],
                        'version': manifest['version'],
                        'author': manifest.get('author', 'Unknown'),
                        'description': manifest.get('description', ''),
                        'manifest': manifest,
                        'extracted_path': str(item),
                        'module_name': module_name,
                        'is_local': True,
                        'status': 'inactive',
                        'enabled': False,
                        'has_settings': has_settings,
                        'settings_schema': settings_schema,
                    }
                )

                if created:
                    logger.info(f"Discovered new plugin: {manifest['name']} v{manifest['version']}")
                    PluginLog.objects.create(
                        plugin=plugin,
                        action='uploaded',
                        message=f"Plugin discovered from folder: {item.name}"
                    )
                else:
                    # Update manifest and settings schema if version changed
                    if plugin.version != manifest['version'] or plugin.settings_schema != settings_schema:
                        plugin.version = manifest['version']
                        plugin.manifest = manifest
                        plugin.has_settings = has_settings
                        plugin.settings_schema = settings_schema
                        plugin.save()
                        logger.info(f"Updated plugin: {manifest['name']} to v{manifest['version']}")

                discovered.append({
                    'plugin': plugin,
                    'manifest': manifest,
                    'path': str(item),
                    'created': created,
                })

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {manifest_path}: {e}")
            except Exception as e:
                logger.error(f"Error discovering plugin in {item.name}: {e}")

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    def validate_zip(self, zip_path: Path) -> Dict[str, Any]:
        """
        Validate plugin ZIP structure and manifest.

        Args:
            zip_path: Path to the ZIP file

        Returns:
            Parsed manifest dict from plugin.json

        Raises:
            ValueError: If ZIP is invalid or missing required files
        """
        logger.info(f"Validating ZIP: {zip_path}")

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Check for plugin.json (can be at root or in subfolder)
                manifest_path = None
                for name in zf.namelist():
                    if name.endswith('plugin.json'):
                        manifest_path = name
                        break

                if not manifest_path:
                    raise ValueError("Missing plugin.json manifest")

                logger.debug(f"Found plugin.json manifest at: {manifest_path}")

                # Parse manifest
                with zf.open(manifest_path) as f:
                    manifest = json.load(f)

                # Validate required fields
                required_fields = ['name', 'slug', 'version']
                missing = [f for f in required_fields if f not in manifest]
                if missing:
                    raise ValueError(f"Missing required fields: {', '.join(missing)}")

                logger.debug(f"Manifest valid: {manifest['name']} v{manifest['version']}")

                # Check for dangerous file extensions
                dangerous_patterns = ['.exe', '.dll', '.so', '.dylib', '.bat', '.cmd']
                for name in zf.namelist():
                    if any(name.lower().endswith(p) for p in dangerous_patterns):
                        raise ValueError(f"Dangerous file detected: {name}")

                logger.info(f"ZIP validation successful: {manifest['name']}")
                return manifest

        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file format")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in plugin.json: {e}")
        except Exception as e:
            logger.error(f"ZIP validation failed: {e}")
            raise

    def extract_plugin(self, plugin_id: str, zip_path: Path) -> Path:
        """
        Extract plugin ZIP to installed directory.

        Args:
            plugin_id: UUID of the plugin
            zip_path: Path to the ZIP file

        Returns:
            Path to extracted plugin directory

        Raises:
            Exception: If extraction fails
        """
        from plugins.models import Plugin

        logger.info(f"Extracting plugin {plugin_id} from {zip_path}")

        try:
            plugin = Plugin.objects.get(pk=plugin_id)
            # Use underscore version for Python module compatibility
            module_dir_name = plugin.slug.replace('-', '_')
            extract_dir = self.PLUGINS_DIR / module_dir_name

            # Remove existing extraction
            if extract_dir.exists():
                logger.debug(f"Removing existing plugin directory: {extract_dir}")
                shutil.rmtree(extract_dir)

            # Extract ZIP
            extract_dir.mkdir(parents=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            logger.debug(f"Extracted to: {extract_dir}")

            # Check if there's a single top-level folder and flatten if needed
            contents = list(extract_dir.iterdir())
            if len(contents) == 1 and contents[0].is_dir():
                # Single folder at root - this is the expected structure from compressed directory
                top_folder = contents[0]
                # Move all contents up one level
                for item in top_folder.iterdir():
                    shutil.move(str(item), str(extract_dir / item.name))
                # Remove empty top folder
                top_folder.rmdir()
                logger.debug(f"Flattened directory structure")

            # Create __init__.py if missing
            init_file = extract_dir / '__init__.py'
            if not init_file.exists():
                init_file.touch()
                logger.debug("Created missing __init__.py")

            logger.info(f"Plugin extraction successful: {extract_dir}")
            return extract_dir

        except Exception as e:
            logger.error(f"Plugin extraction failed: {e}")
            raise

    def load_plugin(self, plugin_id: str) -> bool:
        """
        Load plugin into Django at runtime (hot-load).

        Modifies INSTALLED_APPS, imports plugin module, registers AppConfig,
        and calls ready() method.

        Args:
            plugin_id: UUID of the plugin to load

        Returns:
            True if successful

        Raises:
            Exception: If loading fails
        """
        from plugins.models import Plugin, PluginLog

        logger.info(f"Loading plugin {plugin_id}")

        try:
            plugin = Plugin.objects.get(pk=plugin_id)

            # Add to Python path
            if str(self.PLUGINS_DIR) not in sys.path:
                sys.path.insert(0, str(self.PLUGINS_DIR))
                logger.debug(f"Added {self.PLUGINS_DIR} to sys.path")

            # Determine module name
            # sys.path includes PLUGINS_DIR, so module is just the slug
            module_name = plugin.slug.replace('-', '_')
            plugin.module_name = module_name
            logger.debug(f"Module name: {module_name}")

            # Import plugin module
            plugin_module = importlib.import_module(module_name)
            logger.debug(f"Imported plugin module: {module_name}")

            # Get AppConfig path from manifest
            app_config_path = plugin.manifest.get('django_app', {}).get('app_config')
            if not app_config_path:
                raise ValueError("No app_config specified in manifest")

            # Import AppConfig
            config_module_path, config_class_name = app_config_path.rsplit('.', 1)
            config_module = importlib.import_module(config_module_path)
            app_config_class = getattr(config_module, config_class_name)
            logger.debug(f"Found AppConfig: {app_config_path}")

            # Add to INSTALLED_APPS if not already there
            if module_name not in settings.INSTALLED_APPS:
                settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + [module_name]
                logger.debug(f"Added {module_name} to INSTALLED_APPS")

            # Create and register AppConfig instance
            app_config_instance = app_config_class(module_name, plugin_module)
            apps.app_configs[module_name] = app_config_instance
            logger.debug(f"Registered AppConfig: {module_name}")

            # Call ready() to initialize signals, hooks, etc.
            app_config_instance.ready()
            logger.debug(f"Called AppConfig.ready() for {module_name}")

            # Update plugin status
            plugin.status = 'active'
            plugin.enabled = True
            plugin.activated_at = timezone.now()
            plugin.error_message = ''
            plugin.save()

            # Log the action
            PluginLog.objects.create(
                plugin=plugin,
                action='activated',
                message=f"Plugin activated successfully"
            )

            logger.info(f"Plugin loaded successfully: {plugin.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            plugin.status = 'error'
            plugin.error_message = str(e)
            plugin.save()

            PluginLog.objects.create(
                plugin=plugin,
                action='error',
                message=f"Failed to activate: {str(e)}"
            )
            raise

    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload plugin from Django at runtime (hot-unload).

        Removes from INSTALLED_APPS, removes from app registry,
        and clears from sys.modules.

        Args:
            plugin_id: UUID of the plugin to unload

        Returns:
            True if successful

        Raises:
            Exception: If unloading fails
        """
        from plugins.models import Plugin, PluginLog
        from plugins.hooks import hook_registry

        logger.info(f"Unloading plugin {plugin_id}")

        try:
            plugin = Plugin.objects.get(pk=plugin_id)
            module_name = plugin.module_name

            if not module_name:
                raise ValueError("Plugin has no module_name set")

            # Clear plugin hooks
            try:
                hook_registry.clear_plugin_hooks(module_name)
                logger.debug(f"Cleared hooks for {module_name}")
            except Exception as e:
                logger.warning(f"Failed to clear hooks: {e}")

            # Remove from INSTALLED_APPS
            if module_name in settings.INSTALLED_APPS:
                installed = list(settings.INSTALLED_APPS)
                installed.remove(module_name)
                settings.INSTALLED_APPS = installed
                logger.debug(f"Removed {module_name} from INSTALLED_APPS")

            # Remove from app registry
            if module_name in apps.app_configs:
                del apps.app_configs[module_name]
                logger.debug(f"Removed {module_name} from app registry")

            # Remove from sys.modules
            modules_to_remove = [k for k in list(sys.modules.keys()) if k.startswith(module_name)]
            for mod_name in modules_to_remove:
                del sys.modules[mod_name]
            logger.debug(f"Removed {len(modules_to_remove)} modules from sys.modules")

            # Update plugin status
            plugin.enabled = False
            plugin.status = 'inactive'
            plugin.save()

            # Log the action
            PluginLog.objects.create(
                plugin=plugin,
                action='deactivated',
                message=f"Plugin deactivated successfully"
            )

            logger.info(f"Plugin unloaded successfully: {plugin.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            raise

    def load_all_enabled(self) -> None:
        """
        Load all enabled plugins from database.

        Called on Django startup via AppConfig.ready().
        Skips plugins with errors and logs them.
        """
        from plugins.models import Plugin

        logger.info("Loading all enabled plugins...")

        try:
            enabled_plugins = Plugin.objects.filter(enabled=True)
            logger.info(f"Found {enabled_plugins.count()} enabled plugins")

            for plugin in enabled_plugins:
                try:
                    self.load_plugin(str(plugin.id))
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin.name}: {e}")
                    # Status already updated in load_plugin()

            logger.info("Finished loading enabled plugins")

        except Exception as e:
            logger.error(f"Error loading enabled plugins: {e}")

    def register_plugin_hooks_only(self, plugin_id: str) -> bool:
        """
        Register plugin hooks without modifying INSTALLED_APPS.

        This is safe to call during Django startup.
        Only imports the module and calls ready() to register hooks.

        Args:
            plugin_id: UUID of the plugin

        Returns:
            True if successful
        """
        from plugins.models import Plugin

        try:
            plugin = Plugin.objects.get(pk=plugin_id)

            # Add to Python path
            if str(self.PLUGINS_DIR) not in sys.path:
                sys.path.insert(0, str(self.PLUGINS_DIR))

            module_name = plugin.slug.replace('-', '_')

            # Import plugin module
            plugin_module = importlib.import_module(module_name)

            # Get and import AppConfig
            app_config_path = plugin.manifest.get('django_app', {}).get('app_config')
            if not app_config_path:
                raise ValueError("No app_config specified in manifest")

            config_module_path, config_class_name = app_config_path.rsplit('.', 1)
            config_module = importlib.import_module(config_module_path)
            app_config_class = getattr(config_module, config_class_name)

            # Create instance and call ready() to register hooks only
            # Don't modify apps.app_configs or INSTALLED_APPS
            app_config_instance = app_config_class(module_name, plugin_module)
            app_config_instance.ready()

            logger.info(f"Registered hooks for plugin: {plugin.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to register hooks for plugin {plugin_id}: {e}")
            return False

    def register_all_enabled_hooks(self) -> None:
        """
        Register hooks for all enabled plugins without full loading.

        Safe to call during Django startup.
        """
        from plugins.models import Plugin

        logger.info("Registering hooks for enabled plugins...")

        try:
            enabled_plugins = Plugin.objects.filter(enabled=True)

            for plugin in enabled_plugins:
                try:
                    self.register_plugin_hooks_only(str(plugin.id))
                except Exception as e:
                    logger.warning(f"Could not register hooks for {plugin.name}: {e}")

        except Exception as e:
            logger.error(f"Error registering plugin hooks: {e}")
