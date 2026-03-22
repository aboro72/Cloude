"""
Management command: package_plugins

Creates installable ZIP files from all plugins in plugins/installed/.

Usage:
    python manage.py package_plugins
    python manage.py package_plugins --output /path/to/output
    python manage.py package_plugins --plugin clock_preview
"""

import zipfile
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Package installed plugins into installable ZIP files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output directory for ZIP files (default: plugins/ next to installed/)',
        )
        parser.add_argument(
            '--plugin',
            type=str,
            default=None,
            help='Package only a specific plugin by folder name',
        )

    def handle(self, *args, **options):
        installed_dir = Path(settings.BASE_DIR) / 'plugins' / 'installed'

        if not installed_dir.exists():
            raise CommandError(f'Plugins directory not found: {installed_dir}')

        output_dir = Path(options['output']) if options['output'] else installed_dir.parent / 'packages'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Collect plugin directories to package
        if options['plugin']:
            target = installed_dir / options['plugin']
            if not target.is_dir():
                raise CommandError(f'Plugin not found: {options["plugin"]}')
            candidates = [target]
        else:
            candidates = sorted(
                p for p in installed_dir.iterdir()
                if p.is_dir() and not p.name.startswith(('_', '.'))
            )

        packaged = []
        failed = []

        for plugin_dir in candidates:
            manifest_path = plugin_dir / 'plugin.json'
            if not manifest_path.exists():
                self.stdout.write(self.style.WARNING(f'  Skipped {plugin_dir.name}: no plugin.json'))
                continue

            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

                name = manifest.get('name', plugin_dir.name)
                version = manifest.get('version', '0.0.0')
                zip_name = f"{plugin_dir.name}-{version}.zip"
                zip_path = output_dir / zip_name

                self._create_zip(plugin_dir, zip_path)

                size_kb = zip_path.stat().st_size / 1024
                self.stdout.write(
                    self.style.SUCCESS(f'  Packaged: {name} v{version}  ->  {zip_name}  ({size_kb:.1f} KB)')
                )
                packaged.append(zip_path)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed {plugin_dir.name}: {e}'))
                failed.append(plugin_dir.name)

        self.stdout.write('')
        self.stdout.write(f'Done. {len(packaged)} packaged, {len(failed)} failed.')
        self.stdout.write(f'Output: {output_dir}')

    def _create_zip(self, plugin_dir: Path, zip_path: Path) -> None:
        """
        Pack all files from plugin_dir into zip_path.
        Files are stored at root level (no extra subfolder) so the loader
        can extract them directly into plugins/installed/<slug>/.
        """
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(plugin_dir.rglob('*')):
                # Skip Python bytecode and cache
                if any(part.startswith('__pycache__') for part in file_path.parts):
                    continue
                if file_path.suffix == '.pyc':
                    continue

                if file_path.is_file():
                    arcname = file_path.relative_to(plugin_dir)
                    zf.write(file_path, arcname)
