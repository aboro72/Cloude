from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'platform_auth'

urlpatterns = [
    # Token endpoints
    path('token/', views.PlatformTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Authentication endpoints
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # User endpoints
    path('user/profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('user/change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    # Health check
    path('health/', views.HealthCheckView.as_view(), name='health_check'),
]
