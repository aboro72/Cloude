"""
URL Configuration for CloudService project.
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views.decorators.cache import cache_page

# Home view
class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'CloudService'
        context['app_description'] = 'Nextcloud-ähnlicher Cloud-Service mit Django 5.x'
        return context

urlpatterns = [
    # Home
    path('', HomeView.as_view(), name='home'),

    # Jazzmin Admin (enhanced admin interface)
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # JWT Authentication
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # App URLs
    path('api/', include('api.urls', namespace='api')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('storage/', include('storage.urls', namespace='storage')),
    path('sharing/', include('sharing.urls', namespace='sharing')),
    path('core/', include('core.urls', namespace='core')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Django debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
