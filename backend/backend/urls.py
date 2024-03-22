from django.contrib import admin
from django.urls import include, path
from django.conf import settings


VERSION_API = settings.VERSION_API

urlpatterns = [
    path('admin/', admin.site.urls),
    path(f'api/v{VERSION_API}/', include(f'api.v{VERSION_API}.urls'))
]
