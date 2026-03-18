"""
Standalone script: Creates installable ZIP files from all plugins in plugins/installed/.

Usage:
    python package_plugins.py
    python package_plugins.py --output ./dist
    python package_plugins.py --plugin clock_preview
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).parent
INSTALLED_DIR = BASE_DIR / 'plugins' / 'installed'


def create_zip(plugin_dir: Path, zip_path: Path) -> None:
    """Pack all plugin files into zip_path, stored at root level (no extra subfolder).

    The loader flattens a single top-level folder on extraction, but storing
    files at root is simpler and avoids the ambiguity.
    """
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(plugin_dir.rglob('*')):
            # Skip Python bytecode and cache directories
            if any(part == '__pycache__' for part in file_path.parts):
                continue
            if file_path.suffix == '.pyc':
                continue
            if file_path.is_file():
                arcname = file_path.relative_to(plugin_dir)
                zf.write(file_path, arcname)


def package_plugins(installed_dir: Path, output_dir: Path, only: str | None = None) -> int:
    if not installed_dir.exists():
        print(f'ERROR: Plugins directory not found: {installed_dir}', file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = sorted(
        p for p in installed_dir.iterdir()
        if p.is_dir() and not p.name.startswith(('_', '.'))
    )

    if only:
        candidates = [p for p in candidates if p.name == only]
        if not candidates:
            print(f'ERROR: Plugin "{only}" not found in {installed_dir}', file=sys.stderr)
            return 1

    packaged, failed = 0, 0

    for plugin_dir in candidates:
        manifest_path = plugin_dir / 'plugin.json'
        if not manifest_path.exists():
            print(f'  SKIP  {plugin_dir.name}: no plugin.json')
            continue

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            name = manifest.get('name', plugin_dir.name)
            version = manifest.get('version', '0.0.0')
            zip_name = f'{plugin_dir.name}-{version}.zip'
            zip_path = output_dir / zip_name

            create_zip(plugin_dir, zip_path)

            size_kb = zip_path.stat().st_size / 1024
            print(f'  OK    {name} v{version}  ->  {zip_name}  ({size_kb:.1f} KB)')
            packaged += 1

        except Exception as exc:
            print(f'  FAIL  {plugin_dir.name}: {exc}', file=sys.stderr)
            failed += 1

    print()
    print(f'Done: {packaged} packaged, {failed} failed.')
    print(f'Output: {output_dir.resolve()}')
    return 0 if failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description='Package installed plugins into ZIP files')
    parser.add_argument('--output', default=None, help='Output directory (default: plugins/packages/)')
    parser.add_argument('--plugin', default=None, help='Package only a specific plugin by folder name')
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else INSTALLED_DIR.parent / 'packages'
    sys.exit(package_plugins(INSTALLED_DIR, output_dir, only=args.plugin))


if __name__ == '__main__':
    main()
