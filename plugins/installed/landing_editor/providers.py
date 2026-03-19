import json
from django.urls import reverse
from plugins.ui import PluginMenuItemProvider, PluginPageProvider

DEFAULTS = {
    "color_primary": "#667eea",
    "color_secondary": "#764ba2",
    "hero_badge": "Moderner Cloud-Arbeitsbereich",
    "hero_title_line1": "Dokumente. Teams.",
    "hero_title_line2": "News. Alles an einem Ort.",
    "hero_subtitle": (
        "CloudService vereint Dateiablage, Team-Zusammenarbeit, internes Newsportal "
        "und persönliche Arbeitsbereiche – direkt im Browser, ohne externe Tools."
    ),
    "hero_cta_primary": "Jetzt loslegen",
    "hero_cta_secondary": "Anmelden",
    "stats": [
        {"value": "100%", "label": "Self-hosted & datenschutzkonform"},
        {"value": "∞",    "label": "Benutzer & Teams"},
        {"value": "REST", "label": "Vollständige API inklusive"},
        {"value": "0 €",  "label": "Keine Cloud-Abo-Kosten"},
    ],
    "features_title":    "Alles was ein modernes Intranet braucht",
    "features_subtitle": (
        "Von der persönlichen Dateiablage bis zu teamweiten Newsartikeln – "
        "CloudService wächst mit Ihren Anforderungen."
    ),
    "features": [
        {"icon": "bi-folder2-open",  "title": "Cloud-Speicher",      "text": "Dateien und Ordner sicher speichern, versionieren und von überall abrufen – mit Freigabe-Links und Zugriffssteuerung."},
        {"icon": "bi-people-fill",   "title": "Team Sites",           "text": "Dedizierte Arbeitsbereiche für jedes Team oder Projekt – mit Dokumentbibliothek, News und Mitgliederverwaltung."},
        {"icon": "bi-newspaper",     "title": "Internes Newsportal",  "text": "Unternehmensmeldungen im Magazine-Layout mit Kategorien, Tags, Reaktionen und Kommentarfunktion."},
        {"icon": "bi-grid-1x2-fill", "title": "MySite Hub",           "text": "Persönlicher Arbeitsbereich im SharePoint-Stil: Dateien, Team-News, Freigaben und Abteilungsseiten auf einen Blick."},
        {"icon": "bi-share-fill",    "title": "Flexibles Sharing",    "text": "Dateien per Direktlink, Passwortschutz, Ablaufdatum oder direkt mit Benutzern und Gruppen teilen."},
        {"icon": "bi-plug-fill",     "title": "Plugin-System",        "text": "Erweiterbar durch Plugins: neue Seiten, Menüeinträge und Widgets ohne Änderung am Kernsystem einspielbar."},
    ],
    "steps_title": "In drei Schritten startklar",
    "steps": [
        {"title": "Konto registrieren", "text": "Benutzernamen und Passwort eingeben – in Sekunden einsatzbereit."},
        {"title": "MySite Hub öffnen",  "text": "Der persönliche Arbeitsbereich ist sofort verfügbar – Dateien, News und mehr."},
        {"title": "Team einladen",      "text": "Team Sites erstellen, Mitglieder hinzufügen und gemeinsam arbeiten."},
    ],
    "cta_title":    "Bereit für Ihren Cloud-Arbeitsbereich?",
    "cta_subtitle": "Kostenlos starten – kein Abo, keine versteckten Kosten, vollständig self-hosted.",
    "cta_primary":  "Jetzt registrieren",
    "cta_secondary": "Bereits registriert? Anmelden",
    "footer_company":       "CloudService – ABoro IT",
    "footer_developer":     "Andreas Borowczak",
    "footer_developer_url": "https://aboro-it.net",
}

MYSITE_WIDGET_DEFAULTS = [
    {"id": "news",      "label": "Neuigkeiten",       "icon": "bi-newspaper",    "visible": True},
    {"id": "files",     "label": "Kürzliche Dateien", "icon": "bi-folder2-open", "visible": True},
    {"id": "team_news", "label": "Team News",          "icon": "bi-people-fill",  "visible": True},
    {"id": "teams",     "label": "Abteilungsseiten",   "icon": "bi-building",     "visible": True},
    {"id": "activity",  "label": "Aktivitäten",        "icon": "bi-activity",     "visible": False},
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
    menu_icon  = 'bi-layout-text-window-reverse'
    menu_order = 90

    def get_url(self) -> str:
        return reverse('core:plugin_app', kwargs={'slug': 'landing-editor'})

    def is_visible(self, request) -> bool:
        return request.user.is_authenticated and request.user.is_staff


class LandingEditorPageProvider(PluginPageProvider):
    page_slug  = 'landing-editor'
    page_title = 'Landing Page Editor'
    page_icon  = 'bi-layout-text-window-reverse'

    def get_template_name(self) -> str:
        return 'landing_editor/builder.html'

    def is_visible(self, request) -> bool:
        return request.user.is_staff

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
