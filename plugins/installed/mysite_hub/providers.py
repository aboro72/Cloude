from django.db.models import Q
from django.urls import reverse, reverse_lazy

from core.models import ActivityLog, StorageFile, StorageFolder
from plugins.ui import PluginMenuItemProvider, PluginPageProvider
from plugins.status import is_plugin_enabled
from sharing.models import GroupShare, UserShare


class MySiteMenuProvider(PluginMenuItemProvider):
    menu_label = 'MySite'
    menu_icon = 'bi-grid-1x2-fill'
    menu_order = 30

    def get_url(self) -> str:
        return reverse('core:plugin_app', kwargs={'slug': 'mysite'})

    def is_visible(self, request) -> bool:
        return request.user.is_authenticated and is_plugin_enabled('mysite-hub')


def get_mysite_plugin_settings():
    try:
        from plugins.models import Plugin

        plugin = Plugin.objects.get(slug='mysite-hub')
        return plugin.settings or {}
    except Exception:
        return {}


def parse_lines(value, fallback):
    raw = value or fallback
    return [line.strip() for line in raw.splitlines() if line.strip()]


class DepartmentPageProvider(PluginPageProvider):
    department_slug = ''
    department_title = ''
    department_owner = ''
    department_icon = 'bi-building'
    department_summary = ''
    department_focus = None
    department_links = None
    settings_summary_key = ''
    settings_focus_key = ''

    def get_template_name(self) -> str:
        return 'mysite_hub/department_page.html'

    def get_context(self, request):
        settings = get_mysite_plugin_settings()
        return {
            'hero_title': self.department_title,
            'hero_subtitle': settings.get(self.settings_summary_key, self.department_summary),
            'department_owner': self.department_owner,
            'department_icon': self.department_icon,
            'department_focus': parse_lines(settings.get(self.settings_focus_key, ''), '\n'.join(self.department_focus or [])),
            'department_links': self.department_links or [],
        }


class DepartmentManagementPageProvider(DepartmentPageProvider):
    page_slug = 'department-management'
    page_title = 'Management'
    page_icon = 'bi-bar-chart-line'
    department_title = 'Management Site'
    department_owner = 'Leitung'
    department_icon = 'bi-bar-chart-line'
    department_summary = 'Strategie, Unternehmensziele, Projektpriorisierung und Fuehrungsinformationen.'
    department_focus = ['Quartalsziele', 'Roadmaps', 'Entscheidungen', 'Vorstandsvorlagen']
    settings_summary_key = 'management_summary'
    settings_focus_key = 'management_focus'
    department_links = [
        {'label': 'MySite Hub', 'url': reverse_lazy('core:plugin_app', kwargs={'slug': 'mysite'})},
        {'label': 'Team Sites', 'url': reverse_lazy('sharing:groups_list')},
    ]


class DepartmentPeoplePageProvider(DepartmentPageProvider):
    page_slug = 'department-people'
    page_title = 'Personal'
    page_icon = 'bi-person-vcard'
    department_title = 'People & HR'
    department_owner = 'HR'
    department_icon = 'bi-person-vcard'
    department_summary = 'Onboarding, Richtlinien, Vorlagen und interne Kommunikation fuer Mitarbeitende.'
    department_focus = ['Onboarding', 'Richtlinien', 'Benefits', 'Interne Mitteilungen']
    settings_summary_key = 'people_summary'
    settings_focus_key = 'people_focus'
    department_links = [
        {'label': 'Profile', 'url': reverse_lazy('accounts:profile')},
        {'label': 'MySite Hub', 'url': reverse_lazy('core:plugin_app', kwargs={'slug': 'mysite'})},
    ]


class DepartmentFinancePageProvider(DepartmentPageProvider):
    page_slug = 'department-finance'
    page_title = 'Finanzen'
    page_icon = 'bi-cash-stack'
    department_title = 'Finance Hub'
    department_owner = 'Finance'
    department_icon = 'bi-cash-stack'
    department_summary = 'Budgets, Freigaben, Belege und Monatsabschluesse mit klarer Dokumentstruktur.'
    department_focus = ['Budgetplanung', 'Freigaben', 'Monatsabschluss', 'Lieferantenablage']
    settings_summary_key = 'finance_summary'
    settings_focus_key = 'finance_focus'
    department_links = [
        {'label': 'Dokumentbibliotheken', 'url': reverse_lazy('storage:file_list')},
        {'label': 'MySite Hub', 'url': reverse_lazy('core:plugin_app', kwargs={'slug': 'mysite'})},
    ]


class DepartmentEngineeringPageProvider(DepartmentPageProvider):
    page_slug = 'department-engineering'
    page_title = 'Entwicklung'
    page_icon = 'bi-code-square'
    department_title = 'Engineering Site'
    department_owner = 'Engineering'
    department_icon = 'bi-code-square'
    department_summary = 'Releaseplanung, technische Dokumentation, Deployments und operative Wissenssammlung.'
    department_focus = ['Releaseplaene', 'Architektur', 'Deployments', 'Runbooks']
    settings_summary_key = 'engineering_summary'
    settings_focus_key = 'engineering_focus'
    department_links = [
        {'label': 'Team Sites', 'url': reverse_lazy('sharing:groups_list')},
        {'label': 'Landing Widgets', 'url': reverse_lazy('core:landing')},
    ]


class MySitePageProvider(PluginPageProvider):
    page_slug = 'mysite'
    page_title = 'MySite'
    page_icon = 'bi-grid-1x2-fill'

    def get_template_name(self) -> str:
        return 'mysite_hub/page.html'

    def _build_news_items(self, request):
        from django.utils import timezone as tz
        from django.db.models import Q as DQ

        settings = get_mysite_plugin_settings()

        # Try real NewsArticle objects first
        news = []
        try:
            from news.models import NewsArticle
            articles = NewsArticle.objects.filter(
                is_published=True,
            ).filter(
                DQ(publish_at__isnull=True) | DQ(publish_at__lte=tz.now())
            ).select_related('author', 'category').order_by('-is_pinned', '-publish_at', '-created_at')[:3]

            for article in articles:
                news.append({
                    'title': article.title,
                    'summary': article.summary or article.content[:100],
                    'time': article.publish_at or article.created_at,
                    'icon': article.category.icon if article.category else 'bi-newspaper',
                    'url': f'/news/{article.slug}/',
                })
        except Exception:
            pass

        # Fill up with team news if < 3
        if len(news) < 3:
            try:
                from sharing.models import GroupShare, TeamSiteNews
                user_groups = GroupShare.objects.filter(
                    DQ(owner=request.user) | DQ(members=request.user), is_active=True
                ).values_list('id', flat=True)
                team_articles = TeamSiteNews.objects.filter(
                    group_id__in=user_groups,
                    is_published=True,
                ).filter(
                    DQ(publish_at__isnull=True) | DQ(publish_at__lte=tz.now())
                ).order_by('-created_at')[:3 - len(news)]
                for ta in team_articles:
                    news.append({
                        'title': ta.title,
                        'summary': ta.summary or ta.content[:100],
                        'time': ta.created_at,
                        'icon': 'bi-people',
                        'url': f'/sharing/group/{ta.group_id}/news/{ta.pk}/',
                    })
            except Exception:
                pass

        if news:
            return news

        return [
            {
                'title': settings.get('news_primary_title', 'Willkommen in MySite'),
                'summary': settings.get('news_primary_summary', 'Hier laufen persoenliche Inhalte, Teamseiten und Dokumentbereiche zusammen.'),
                'time': None,
                'icon': 'bi-stars',
                'url': '/news/',
            },
            {
                'title': settings.get('news_secondary_title', 'Alle News ansehen'),
                'summary': settings.get('news_secondary_summary', 'Aktuelle Unternehmensmeldungen und Ankündigungen im News-Bereich.'),
                'time': None,
                'icon': 'bi-megaphone',
                'url': '/news/',
            },
        ]

    def _build_team_sites(self, request):
        group_shares = GroupShare.objects.filter(Q(owner=request.user) | Q(members=request.user), is_active=True).distinct().order_by('-created_at')[:3]
        team_sites = []

        for share in group_shares:
            can_manage = share.user_can_manage(request.user)
            team_sites.append({
                'title': share.group_name,
                'description': f'Gruppenbereich mit {share.members.count()} Mitgliedern und Berechtigung {share.get_permission_display()}.',
                'meta': 'Team Site',
                'url': reverse('sharing:group_detail', kwargs={'group_id': share.id}),
                'icon': 'bi-people-fill',
                'can_manage': can_manage,
                'news_create_url': reverse('sharing:team_news_create', kwargs={'group_id': share.id}) if can_manage else None,
            })

        if team_sites:
            return team_sites

        return [
            {
                'title': 'Projektboard',
                'description': 'Vorlage fuer Status, Dokumente, Aufgaben und gemeinsame Ablage.',
                'meta': 'Empfohlene Site',
                'url': reverse('sharing:groups_list'),
                'icon': 'bi-kanban',
            },
            {
                'title': 'Vertrieb',
                'description': 'Angebote, Freigaben, Kundendokumente und Team-News an einem Ort.',
                'meta': 'Abteilungs-Site',
                'url': reverse('sharing:groups_list'),
                'icon': 'bi-briefcase',
            },
            {
                'title': 'IT Operations',
                'description': 'Runbooks, Releases, technische Doku und operative Uebersichten.',
                'meta': 'Operations-Site',
                'url': reverse('sharing:groups_list'),
                'icon': 'bi-cpu',
            },
        ]

    def _build_document_libraries(self, request):
        folders = StorageFolder.objects.filter(owner=request.user, parent__isnull=True).order_by('-updated_at')[:4]
        libraries = []

        for folder in folders:
            libraries.append({
                'title': folder.name,
                'description': folder.description or 'Persoenliche Dokumentbibliothek',
                'count': folder.files.count(),
                'meta': folder.get_path(),
                'url': reverse('storage:folder', kwargs={'folder_id': folder.id}),
            })

        if libraries:
            return libraries

        return [
            {'title': 'Vertraege', 'description': 'Vertragsunterlagen und Freigaben', 'count': 0, 'meta': '/Vertraege', 'url': reverse('storage:file_list')},
            {'title': 'Projekte', 'description': 'Projektakten und Teamdokumente', 'count': 0, 'meta': '/Projekte', 'url': reverse('storage:file_list')},
            {'title': 'Wissen', 'description': 'Richtlinien, Vorlagen und Handbuecher', 'count': 0, 'meta': '/Wissen', 'url': reverse('storage:file_list')},
        ]

    def _build_department_pages(self):
        try:
            from departments.models import Department
            depts = Department.objects.select_related('head').order_by('name')[:8]
            if depts:
                result = []
                for d in depts:
                    result.append({
                        'title': d.name,
                        'description': d.description or '',
                        'owner': d.head.get_full_name() or d.head.username if d.head else '',
                        'icon': d.icon,
                        'color': d.color,
                        'url': reverse('departments:detail', kwargs={'slug': d.slug}),
                    })
                return result
        except Exception:
            pass
        # fallback wenn noch keine Abteilungen angelegt
        return [
            {
                'title': 'Abteilungen',
                'description': 'Noch keine Abteilungen angelegt.',
                'owner': '',
                'icon': 'bi-building',
                'color': '#667eea',
                'url': reverse('departments:list'),
            },
        ]

    def _build_webparts(self):
        return [
            {'title': 'News Feed', 'description': 'Aktuelle Meldungen prominent auf jeder Site.', 'icon': 'bi-newspaper'},
            {'title': 'Dokumentenliste', 'description': 'Dateien, Bibliotheken und letzte Aenderungen.', 'icon': 'bi-journal-richtext'},
            {'title': 'Schnelllinks', 'description': 'Wichtige Ziele fuer Team und Bereich.', 'icon': 'bi-link-45deg'},
            {'title': 'Personen', 'description': 'Kontakte, Owner und Team-Mitglieder sichtbar machen.', 'icon': 'bi-people'},
            {'title': 'Aktivitaeten', 'description': 'Uploads, Freigaben und aktuelle Arbeitsschritte.', 'icon': 'bi-activity'},
            {'title': 'Widgets', 'description': 'Bestehende Dashboard-Widgets als Site-Bausteine nutzen.', 'icon': 'bi-grid-3x3-gap'},
        ]

    def get_template_name(self) -> str:
        return 'mysite_hub/page.html'

    def get_context(self, request):
        settings = get_mysite_plugin_settings()
        profile = request.user.profile
        recent_files = StorageFile.objects.filter(owner=request.user).order_by('-updated_at')[:5]
        incoming_shares = UserShare.objects.filter(shared_with=request.user, is_active=True).order_by('-created_at')[:4]

        return {
            'hero_title': f"MySite von {request.user.get_full_name() or request.user.username}",
            'hero_subtitle': settings.get('mysite_intro', 'Persoenlicher Arbeitsbereich fuer Dokumente, Teams, News und moderne Bereichsseiten im SharePoint-Stil.'),
            'hero_style': profile.mysite_hero_style,
            'hero_image_url': profile.mysite_hero_image.url if profile.mysite_hero_image else '',
            'hero_video_url': profile.mysite_hero_video.url if profile.mysite_hero_video else '',
            'storage_used_mb': profile.get_storage_used_mb(),
            'storage_remaining_mb': profile.get_storage_remaining_mb(),
            'storage_percent': round(profile.get_storage_used_percentage(), 1),
            'quick_links': [
                {'title': 'Meine Dateien', 'description': 'Dokumente, Uploads und Ordner an einem Ort.', 'url': reverse('storage:file_list'), 'icon': 'bi-folder2-open'},
                {'title': 'Geteilte Inhalte', 'description': 'Freigegebene Dateien und Zusammenarbeit.', 'url': reverse('sharing:shared_with_me'), 'icon': 'bi-people'},
                {'title': 'Profil', 'description': 'Persoenliche Angaben, Avatar und Design verwalten.', 'url': reverse('accounts:profile'), 'icon': 'bi-person-badge'},
                {'title': 'Landing', 'description': 'Widgets und persoenliche Startansicht.', 'url': reverse('core:landing'), 'icon': 'bi-speedometer2'},
            ],
            'news_items': self._build_news_items(request),
            'team_sites': self._build_team_sites(request),
            'document_libraries': self._build_document_libraries(request),
            'department_pages': self._build_department_pages(),
            'webparts': self._build_webparts(),
            'recent_files': recent_files,
            'incoming_shares': incoming_shares,
        }
