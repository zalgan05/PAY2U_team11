from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (extend_schema,)

from subscriptions.models import (
    Subscription,
)
from .serializers import (
    SubscriptionSerializer,
    SubscriptionDetailSerializer,
    IsFavoriteSerializer,
    SubscriptionOrderSerializer
)
from .filters import SubscriptionFilter


@extend_schema(tags=['Сервисы подписок'])
class SubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = SubscriptionFilter

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubscriptionDetailSerializer
        return super().get_serializer_class()

    @extend_schema(
        request=None,
        responses={status.HTTP_201_CREATED: None},
    )
    @action(detail=True, methods=['post'])
    def favorite(self, request, pk):
        """Добавляет подписку в избранное для текущего пользователя."""
        serializer = IsFavoriteSerializer(
            data={},
            context={'request': request, 'sub_id': pk}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)

    @extend_schema(
        request=None,
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        """Удаляет подписку из избранного для текущего пользователя."""
        serializer = IsFavoriteSerializer(
            data={},
            context={'request': request, 'sub_id': pk}
        )
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request={
                'items': {
                    'type': 'object',
                    'properties': {
                        'name_subscriber': {'type': 'string'},
                        'phone_number': {'type': 'integer'},
                        'email': {'type': 'string', 'format': 'email'},
                        'tariff': {'type': 'integer'},
                    }
                }
            },
        responses={201: SubscriptionOrderSerializer}
    )
    @action(detail=True, methods=['post',])
    def order(self, request, pk):
        """Создает заказ на подписку сервиса."""
        serializer = SubscriptionOrderSerializer(
            data=request.data,
            context={'request': request, 'sub_id': pk}
        )
        serializer.is_valid(raise_exception=True)
        subscription = Subscription.objects.get(id=pk)
        serializer.save(
            user=self.request.user,
            subscription=subscription
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
