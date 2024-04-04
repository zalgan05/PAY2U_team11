from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularSwaggerView,
    SpectacularAPIView,
    SpectacularRedocView
)

from .views import (
    CategorySubscriptionViewSet,
    HistoryViewSet,
    SubscriptionViewSet
)


router = DefaultRouter()
router.register('subscriptions', SubscriptionViewSet, basename='subscription')
router.register(
    'categories',
    CategorySubscriptionViewSet,
    basename='categories'
)
router.register('history', HistoryViewSet, basename='history')

urlpatterns = [
    path('', include(router.urls)),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='docs'
    ),
    path(
        'redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),
]
