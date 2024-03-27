from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (extend_schema, extend_schema_view)

from subscriptions.models import (
    CategorySubscription,
    Subscription,
)
from .serializers import (
    CategorySubscriptionSerializer,
    SubscriptionSerializer,
    SubscriptionDetailSerializer,
    IsFavoriteSerializer,
    SubscriptionOrderSerializer
)
from .filters import SubscriptionFilter


@extend_schema(tags=['Сервисы подписок'])
@extend_schema_view(
    list=extend_schema(
        summary='Получить список всех сервисов',
    ),
    retrieve=extend_schema(
        summary='Получить детальную информацию одного сервиса',
    )
)
class SubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """Позволяет просматривать список доступных подписок."""

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
        summary='Добавить сервис в избранное'
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
        summary='Удалить сервис из избранного'
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
                        'name': {'type': 'string'},
                        'phone_number': {'type': 'integer'},
                        'email': {'type': 'string', 'format': 'email'},
                        'tariff': {'type': 'integer'},
                    }
                }
            },
        responses={201: SubscriptionOrderSerializer},
        summary='Оформить подписку'
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


@extend_schema(tags=['Категории сервисов'], summary='Список всех категорий')
class CategorySubscriptionViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """Возвращает список доступных категорий сервисов."""

    queryset = CategorySubscription.objects.all()
    serializer_class = CategorySubscriptionSerializer
