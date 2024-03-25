from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
# from django.shortcuts import get_object_or_404

from subscriptions.models import (
    # IsFavoriteSubscription,
    Subscription,
)
from .serializers import (
    SubscriptionSerializer,
    SubscriptionDetailSerializer,
    IsFavoriteSerializer
)


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

    @action(detail=True, methods=['post'])
    def favorite(self, request, pk):
        """Добавляет подписку в избранное для текущего пользователя."""
        serializer = IsFavoriteSerializer(
            data=request.data,
            context={'request': request, 'sub_id': pk}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        """Удаляет подписку из избранного для текущего пользователя."""
        serializer = IsFavoriteSerializer(
            data=request.data,
            context={'request': request, 'recipe_id': pk}
        )
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
