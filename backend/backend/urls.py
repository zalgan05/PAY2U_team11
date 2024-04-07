from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from rest_framework.authtoken import views


VERSION_API = settings.VERSION_API

urlpatterns = [
    path('admin/', admin.site.urls),
    path(f'api/v{VERSION_API}/', include(f'api.v{VERSION_API}.urls')),
    path('api-token-auth/', views.obtain_auth_token),
]
