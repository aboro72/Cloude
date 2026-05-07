import json

from django.urls import reverse

from plugins.status import is_plugin_enabled
from plugins.ui import PluginMenuItemProvider, PluginPageProvider


DEFAULTS = {
    "color_primary": "#667eea",
    "color_secondary": "#764ba2",
    "hero_badge": "Moderner Firmen-Workspace",
    "hero_title_line1": "Firmen. Teams.",
    "hero_title_line2": "Mitarbeiter. Alles an einem Ort.",
    "hero_subtitle": (
        "CloudService vereint mehrere Firmen auf einer Plattform: mit eigenem "
        "Verzeichnis oder eigener Subdomain pro Firma, Team-Bereichen, "
        "Mitarbeiterverzeichnis und gemeinsamen Arbeitsbereichen."
    ),
    "hero_cta_primary": "Jetzt loslegen",
    "hero_cta_secondary": "Anmelden",
    "stats": [
        {"value": "100%", "label": "Self-hosted & datenschutzkonform"},
        {"value": "Multi", "label": "Firmen, Teams & Mitarbeiter"},
        {"value": "REST", "label": "Vollstaendige API inklusive"},
        {"value": "5", "label": "Mitarbeiter pro Firma kostenfrei"},
    ],
    "features_title": "Alles was ein modernes Firmenportal braucht",
    "features_subtitle": (
        "Von Firmen-Workspaces ueber Teams bis zum Mitarbeiterverzeichnis - "
        "CloudService waechst mit mehreren Unternehmen auf einer Plattform."
    ),
    "features": [
        {
            "icon": "bi-building",
            "title": "Firmen-Workspaces",
            "text": "Jede Firma erhaelt einen eigenen Bereich - wahlweise als Verzeichnis oder Subdomain mit klarer Trennung.",
        },
        {
            "icon": "bi-folder2-open",
            "title": "Cloud-Speicher",
            "text": "Dateien und Ordner sicher speichern, versionieren und von ueberall abrufen - mit Freigabe-Links und Zugriffssteuerung.",
        },
        {
            "icon": "bi-people-fill",
            "title": "Team Sites",
            "text": "Dedizierte Arbeitsbereiche fuer jedes Team oder Projekt - mit Dokumentbibliothek, News und Mitgliederverwaltung.",
        },
        {
            "icon": "bi-person-badge",
            "title": "Mitarbeiterverzeichnis",
            "text": "Mitarbeiter, Rollen, Abteilungen und Zustaendigkeiten strukturiert pro Firma verwalten.",
        },
        {
            "icon": "bi-grid-1x2-fill",
            "title": "MySite Hub",
            "text": "Persoenlicher Arbeitsbereich im SharePoint-Stil: Dateien, Team-News, Freigaben und Abteilungsseiten auf einen Blick.",
        },
        {
            "icon": "bi-cash-coin",
            "title": "5 Mitarbeiter frei",
            "text": "Bis zu 5 Mitarbeiter pro registrierter Firma sind kostenfrei enthalten - ideal fuer den Einstieg.",
        },
    ],
    "steps_title": "In drei Schritten startklar",
    "steps": [
        {
            "title": "Firma registrieren",
            "text": "Firmennamen anlegen und Verzeichnis oder Subdomain fuer den Workspace festlegen.",
        },
        {
            "title": "Workspace aktivieren",
            "text": "Der Firmenbereich steht sofort fuer Teams, Dateien und News bereit.",
        },
        {
            "title": "Mitarbeiter einladen",
            "text": "Bis zu 5 Mitarbeiter kostenfrei hinzufuegen und gemeinsam arbeiten.",
        },
    ],
    "cta_title": "Bereit fuer Ihren Firmen-Workspace?",
    "cta_subtitle": (
        "Mehrere Firmen registrieren, eigene Bereiche vergeben und mit bis zu 5 "
        "Mitarbeitern kostenfrei starten."
    ),
    "cta_primary": "Jetzt registrieren",
    "cta_secondary": "Bereits registriert? Anmelden",
    "footer_company": "CloudService - ABoro IT",
    "footer_developer": "Andreas Borowczak",
    "footer_developer_url": "https://aboro-it.net",
}

MYSITE_WIDGET_DEFAULTS = [
    {"id": "news", "label": "Neuigkeiten", "icon": "bi-newspaper", "visible": True},
    {"id": "files", "label": "Kuerzliche Dateien", "icon": "bi-folder2-open", "visible": True},
    {"id": "team_news", "label": "Team News", "icon": "bi-people-fill", "visible": True},
    {"id": "teams", "label": "Abteilungsseiten", "icon": "bi-building", "visible": True},
    {"id": "activity", "label": "Aktivitaeten", "icon": "bi-activity", "visible": False},
]


def get_landing_settings() -> dict:
    """Load settings from DB, merged with defaults. Never raises."""
    try:
        from plugins.models import Plugin

        plugin = Plugin.objects.get(slug='landing-editor')
        merged = dict(DEFAULTS)
        merged.update(plugin.settings or {})
        return merged
    except Exception:
        return dict(DEFAULTS)


def get_page_content(page_slug: str) -> dict:
    """Returns {'html': str, 'css': str} for a GrapesJS-managed page."""
    try:
        lp = get_landing_settings()
        pages = lp.get('pages', {})
        return pages.get(page_slug, {'html': '', 'css': ''})
    except Exception:
        return {'html': '', 'css': ''}


def get_mysite_widgets() -> list:
    """Returns the widget config list for MySite Hub."""
    lp = get_landing_settings()
    saved = lp.get('mysite_widgets')
    if saved and isinstance(saved, list):
        return saved
    return list(MYSITE_WIDGET_DEFAULTS)


class LandingEditorMenuProvider(PluginMenuItemProvider):
    menu_label = 'Landingpage'
    menu_icon = 'bi-layout-text-window-reverse'
    menu_order = 90

    def get_url(self) -> str:
        return reverse('core:plugin_app', kwargs={'slug': 'landing-editor'})

    def is_visible(self, request) -> bool:
        return (
            request.user.is_authenticated
            and request.user.is_staff
            and is_plugin_enabled('landing-editor')
        )


class LandingEditorPageProvider(PluginPageProvider):
    page_slug = 'landing-editor'
    page_title = 'Landing Page Editor'
    page_icon = 'bi-layout-text-window-reverse'

    def get_template_name(self) -> str:
        return 'landing_editor/builder.html'

    def is_visible(self, request) -> bool:
        return request.user.is_staff and is_plugin_enabled('landing-editor')

    def get_context(self, request) -> dict:
        settings_data = get_landing_settings()
        pages = settings_data.get('pages', {})
        return {
            'lp': settings_data,
            'lp_json': json.dumps(settings_data, ensure_ascii=False),
            'pages_json': json.dumps(pages, ensure_ascii=False),
            'mysite_widgets_json': json.dumps(get_mysite_widgets(), ensure_ascii=False),
            'save_url': reverse('landing_editor:save'),
            'defaults_json': json.dumps(DEFAULTS, ensure_ascii=False),
        }
