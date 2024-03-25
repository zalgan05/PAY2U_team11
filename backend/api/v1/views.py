from rest_framework import viewsets, mixins

from subscriptions.models import (
    Subscription,
)
from .serializers import SubscriptionSerializer, SubscriptionDetailSerializer


class SubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubscriptionDetailSerializer
        return super().get_serializer_class()
