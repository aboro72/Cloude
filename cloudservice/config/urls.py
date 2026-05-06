"""
URL Configuration for CloudService project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core import views as core_views
from messenger import views as messenger_views


urlpatterns = [
    path('', core_views.home, name='home'),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('settings/', core_views.settings, name='settings'),
    path('debug/plugins/', core_views.debug_plugins, name='debug_plugins'),
    path('api/', include('api.urls', namespace='api')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('storage/', include('storage.urls', namespace='storage')),
    path('sharing/', include('sharing.urls', namespace='sharing')),
    path('core/', include('core.urls', namespace='core')),
    path('news/', include('news.urls', namespace='news')),
    path('landing-editor/', include('landing_editor.urls', namespace='landing_editor')),
    path('tasks/', include('tasks_board.urls', namespace='tasks_board')),
    path('forms/', include('forms_builder.urls', namespace='forms_builder')),
    path('departments/', include('departments.urls', namespace='departments')),
    # Global messenger invite (cross-company)
    path('messenger/invite/<uuid:token>/', messenger_views.invite_accept, name='messenger_invite'),
    # Global messenger redirect — leitet zur Firma des Users weiter
    path('messenger/', messenger_views.messenger_redirect, name='messenger_global'),
]

# Media serving — explicit so it works even with DEBUG=False (runserver dev mode).
# Must come before the <workspace_key> slug catch-all.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Company workspace routes — slug catch-all must come last
urlpatterns += [
    path('firmen/<slug:workspace_key>/', core_views.company_home_redirect, name='company_home_legacy'),
    path('<slug:workspace_key>/mysite/', core_views.company_home_redirect, name='company_home_mysite_legacy'),
    path('<slug:workspace_key>/', core_views.company_home, name='company_home'),
    path('<slug:workspace_key>/settings/', core_views.company_landing_settings, name='company_landing_settings'),
    path('<slug:workspace_key>/builder/', core_views.company_landing_builder, name='company_landing_builder'),
    path('<slug:workspace_key>/builder/save/', core_views.company_landing_builder_save, name='company_landing_builder_save'),
    path('<slug:workspace_key>/mitglieder/', core_views.company_members, name='company_members'),
    path('<slug:workspace_key>/messenger/', include('messenger.urls', namespace='messenger')),
]

if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
