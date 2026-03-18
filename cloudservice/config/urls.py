"""
URL Configuration for CloudService project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core import views as core_views


class HomeRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return '/core/apps/mysite/'
        return '/accounts/login/'


urlpatterns = [
    path('', HomeRedirectView.as_view(), name='home'),
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
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
