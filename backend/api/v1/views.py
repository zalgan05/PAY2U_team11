from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter
)

from subscriptions.models import (
    CategorySubscription,
    Subscription,
    Tariff,
)
from .serializers import (
    CategorySubscriptionSerializer,
    MySubscriptionSerializer,
    SubscriptionSerializer,
    SubscriptionDetailSerializer,
    IsFavoriteSerializer,
    SubscriptionOrderSerializer,
    TariffSerializer
)
from .filters import (
    SubscriptionFilter,
)


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
        responses={status.HTTP_200_OK: TariffSerializer(many=True)},
        summary='Получить все тарифы подписки'
    )
    @action(detail=True, methods=['get'], filterset_class=None)
    def tariffs(self, request, pk):
        """Получить все тарифы сервиса подписок."""
        tariffs = Tariff.objects.filter(subscription=pk)
        serializer = TariffSerializer(tariffs, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Мои подписки'],
        responses={
            status.HTTP_200_OK: TariffSerializer,
            status.HTTP_404_NOT_FOUND: {'error': 'Тариф не найден'}
        },
        summary='Получить мой тариф подписки'
    )
    @action(detail=True, methods=['get'])
    def mytariff(self, request, pk):
        """Получить мой тариф подписки на сервис."""
        user = request.user
        try:
            subscription = Subscription.objects.get(orders__user=user, id=pk)
            tariff = subscription.orders.select_related('tariff').get().tariff
            serializer = TariffSerializer(tariff)
            return Response(serializer.data)
        except Exception:
            return Response(
                {'error': 'Тариф не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

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

    @extend_schema(
        tags=['Мои подписки'],
        summary='Получить мои подписки',
        responses={200: MySubscriptionSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                location=OpenApiParameter.QUERY,
                name='pay_status',
                required=False,
                type=bool
            ),
        ]
    )
    @action(detail=False, methods=['get'], filterset_class=None)
    def my(self, request, *args, **kwargs):
        """
        Получает подписки текущего пользователя.

        Parameters:
        - pay_status (bool, optional): Фильтр по статусу оплаты подписок.
            Позволяет фильтровать подписки по статусу оплаты.
            Если передано значение True, возвращаются подписки
            со статусом оплаты "оплачено".
            Если передано значение False, возвращаются подписки
            со статусом оплаты "не оплачено".
        """
        pay_status = self.request.query_params.get('pay_status', '').lower()

        user = request.user
        subscriptions = Subscription.objects.filter(orders__user=user)

        if pay_status == 'true':
            subscriptions = subscriptions.filter(orders__pay_status=True)
        elif pay_status == 'false':
            subscriptions = subscriptions.filter(orders__pay_status=False)

        serializer = MySubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)

    def dispatch(self, request, *args, **kwargs):
        res = super().dispatch(request, *args, **kwargs)
        from django.db import connection
        print(len(connection.queries))
        for q in connection.queries:
            print('>>>>>>', q['sql'])
        return res


@extend_schema(tags=['Категории сервисов'], summary='Список всех категорий')
class CategorySubscriptionViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """Возвращает список доступных категорий сервисов."""

    queryset = CategorySubscription.objects.all()
    serializer_class = CategorySubscriptionSerializer
