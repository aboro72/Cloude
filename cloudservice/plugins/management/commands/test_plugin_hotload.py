import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command

from plugins.loader import PluginLoader


class Command(BaseCommand):
    help = "Testet Plugin-Aktivierung/Deaktivierung ohne Django-Neustart mit frischer SQLite-DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            default="landing-editor",
            help="Slug des zu ladenden Test-Plugins (Standard: landing-editor).",
        )

    def handle(self, *args, **options):
        slug = options["slug"]

        tmp_root = Path(tempfile.mkdtemp(prefix="plugin_hotload_"))
        tmp_db = tmp_root / "db.sqlite3"
        tmp_plugins = tmp_root / "plugins_installed"
        tmp_plugins.mkdir(parents=True, exist_ok=True)

        # Lokale Kopie des Plugins erzeugen, damit der Repo-Inhalt unveraendert bleibt.
        src = Path(settings.BASE_DIR) / "plugins" / "installed" / slug.replace("-", "_")
        if not src.exists():
            src = Path(settings.BASE_DIR) / "plugins" / "installed" / slug
        if not src.exists():
            self.stderr.write(f"Plugin-Quellpfad nicht gefunden: {src}")
            return
        shutil.copytree(src, tmp_plugins / src.name)

        # Auf frische SQLite-DB umschalten und Migrationen laufen lassen.
        settings.DATABASES["default"]["ENGINE"] = "django.db.backends.sqlite3"
        settings.DATABASES["default"]["NAME"] = str(tmp_db)
        call_command("migrate", verbosity=0)

        loader = PluginLoader()
        loader.PLUGINS_DIR = tmp_plugins

        discovered = loader.discover_plugins()
        if not discovered:
            self.stderr.write("Kein Plugin entdeckt.")
            return

        plugin = discovered[0]["plugin"]
        self.stdout.write(f"Entdeckt: {plugin.slug} ({plugin.id})")

        loader.load_plugin(str(plugin.id))
        plugin.refresh_from_db()
        self.stdout.write(f"Aktiviert: enabled={plugin.enabled}, status={plugin.status}")

        loader.unload_plugin(str(plugin.id))
        plugin.refresh_from_db()
        self.stdout.write(f"Deaktiviert: enabled={plugin.enabled}, status={plugin.status}")

        self.stdout.write(f"Test-DB: {tmp_db}")
        self.stdout.write(f"Test-Plugins: {tmp_plugins}")
