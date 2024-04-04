from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework import viewsets, mixins, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Min
from django.db import transaction
from django.utils import timezone

from dateutil.relativedelta import relativedelta
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiTypes
)
from celery.result import AsyncResult

from .services import (
    bank_operation,
    get_cashback_transactions_period,
    get_transaction_totals,
)
from subscriptions.models import (
    CategorySubscription,
    Subscription,
    SubscriptionUserOrder,
    Tariff,
    Transaction,
)
from .serializers import (
    CategorySubscriptionSerializer,
    HistoryTransactionSerializator,
    InfoTransactionSerializator,
    MySubscriptionSerializer,
    MyTariffSerializer,
    MyTariffUpdateSerializer,
    SubscriptionCatalogSerializer,
    SubscriptionSerializer,
    SubscriptionDetailSerializer,
    IsFavoriteSerializer,
    SubscriptionOrderSerializer,
    TariffSerializer
)
from .filters import (
    HistoryFilter,
    SubscriptionFilter,
)
from .tasks import next_bank_transaction, update_pay_status_and_due_date


@extend_schema(tags=['Сервисы подписок'])
@extend_schema_view(
    list=extend_schema(
        summary='Получить список всех сервисов',
        parameters=[
            OpenApiParameter(
                location=OpenApiParameter.QUERY,
                name='ordering',
                required=False,
                description='Поля для сортировки',
                type=str,
                enum=['name', 'popular_rate']
            ),
        ]
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

    # queryset = Subscription.objects.annotate(
    #     min_price=Min('tariffs__price_per_month')
    # ).prefetch_related('categories',)
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = SubscriptionFilter
    ordering_fields = ('name', 'popular_rate')
    ordering = ('-name',)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubscriptionDetailSerializer
        elif self.action == 'list':
            return SubscriptionCatalogSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            return queryset.annotate(
                min_price=Min('tariffs__price_per_month')
            ).prefetch_related('categories',)
        elif self.action == 'retrieve':
            return queryset.prefetch_related(
                'categories',
                'banners',
            )
        return queryset

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
            status.HTTP_200_OK: MyTariffSerializer,
            status.HTTP_404_NOT_FOUND: {'error': 'Тариф не найден'}
        },
        summary='Получить мой тариф подписки'
    )
    @action(detail=True, methods=['get'])
    def mytariff(self, request, pk):
        """Получить мой тариф подписки на сервис."""
        user = request.user
        try:
            subscription = Subscription.objects.get(id=pk)
            order = SubscriptionUserOrder.objects.select_related('tariff').get(
                user=user,
                subscription=subscription
            )
            serializer = MyTariffSerializer(order)
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
        responses={status.HTTP_201_CREATED: SubscriptionOrderSerializer},
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
        order = serializer.save(
            user=self.request.user,
            subscription=subscription
        )
        # TEst
        task = next_bank_transaction.apply_async(
            args=[order.id], eta=timezone.now() + relativedelta(seconds=10)
        )

        # task = next_bank_transaction.apply_async(
        #     args=[order.id], eta=order.due_date
        # )
        order.task_id_celery = task.id
        order.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=['Мои подписки'],
        request=None,
        responses={status.HTTP_200_OK: None},
        summary='Возобновить подписку'
    )
    @action(detail=True, methods=['post',])
    def resume_order(self, request, pk):
        """Возобновляет подписку уже существовавшую ранее у пользователя."""
        try:
            subscription = get_object_or_404(Subscription, id=pk)
            order = (
                SubscriptionUserOrder.objects
                .select_related('subscription')
                .get(user=request.user, subscription=subscription)
            )
            if order.pay_status:
                print('Yeas')
                raise ValidationError(
                    'Подписка уже оплачена и не может быть возобновлена'
                )
            with transaction.atomic():
                order.due_date = (
                    timezone.now() +
                    relativedelta(months=(order.tariff.period))
                )
                bank_operation(
                    self.request.user, subscription, order.tariff, order
                )
                order.pay_status = True
            # TEst
            task = next_bank_transaction.apply_async(
                args=[order.id], eta=timezone.now() + relativedelta(seconds=10)
            )

            # task = next_bank_transaction.apply_async(
            #     args=[order.id], eta=order.due_date
            # )
            order.task_id_celery = task.id
            order.save()
            return Response(status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'error': e}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Мои подписки'],
        summary='Получить мои подписки',
        responses={status.HTTP_200_OK: MySubscriptionSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                location=OpenApiParameter.QUERY,
                name='pay_status',
                required=False,
                type=bool
            )
        ],
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

        orders = SubscriptionUserOrder.objects.filter(
            user=user
        ).select_related('subscription', 'tariff')

        if pay_status in ('true', 'false'):
            pay_status_bool = pay_status == 'true'
            orders = orders.filter(pay_status=pay_status_bool)

        serializer = MySubscriptionSerializer(orders, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Мои подписки'],
        summary='Изменить тариф моей подписки',
        request={
            'items': {
                    'type': 'object',
                    'properties': {
                        'tariff': {'type': 'integer'},
                    }
                }
        },
        responses={status.HTTP_200_OK: MyTariffUpdateSerializer()}
    )
    @action(detail=True, methods=['patch'])
    def change_tariff(self, request, pk):
        """
        Позволяет заменить текущий тариф подписки пользователя на новый тариф.
        В теле запроса ожидается id нового тарифа.
        """
        subscription = get_object_or_404(Subscription, id=pk)
        order = (
            SubscriptionUserOrder.objects
            .select_related('subscription')
            .get(user=request.user, subscription=subscription)
        )
        serializer = MyTariffUpdateSerializer(
            order, data=request.data, partial=True,
            context={'request': request, 'subscription': subscription}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Мои подписки'],
        summary='Отменить подписку',
        responses={status.HTTP_200_OK: None},
    )
    @action(detail=True, methods=['delete'])
    def cancel(self, request, pk):
        """Отменяет подписку пользователя на указанный сервис."""
        try:
            subscription = get_object_or_404(Subscription, id=pk)
            order = (
                SubscriptionUserOrder.objects
                .select_related('subscription')
                .get(user=request.user, subscription=subscription)
            )
            if not order.pay_status:
                raise ValidationError(
                    'Подписка уже отменена и не может быть отменена повторно.'
                )
            task_id = order.task_id_celery
            if task_id:
                AsyncResult(task_id).revoke(terminate=True)
            Transaction.objects.get(
                user=self.request.user,
                order=order,
                transaction_type='DEBIT',
                status='PENDING'
            ).delete()
            # update_pay_status_and_due_date.apply_async(
            #     args=[order.id], eta=order.due_date
            # )
            # Test
            update_pay_status_and_due_date.apply_async(
                args=[order.id], eta=timezone.now() + relativedelta(seconds=10)
            )
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response(
                {'error': 'Подписка у пользователя не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response({'error': e}, status=status.HTTP_400_BAD_REQUEST)

    # def dispatch(self, request, *args, **kwargs):
    #     res = super().dispatch(request, *args, **kwargs)
    #     from django.db import connection
    #     print(len(connection.queries))
    #     for q in connection.queries:
    #         print('>>>>>>', q['sql'])
    #     return res


@extend_schema(tags=['Категории сервисов'], summary='Список всех категорий')
class CategorySubscriptionViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """Возвращает список доступных категорий сервисов."""

    queryset = CategorySubscription.objects.all()
    serializer_class = CategorySubscriptionSerializer


@extend_schema(tags=['История операций'], summary='Список всех операций')
class HistoryViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """Позволяет просматривать истории транзакций."""

    serializer_class = HistoryTransactionSerializator
    filter_backends = (DjangoFilterBackend,)
    filterset_class = HistoryFilter
    queryset = Transaction.objects.all()

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user)
        if self.action == 'list':
            return (
                qs.select_related('order')
                .prefetch_related('order__subscription__categories')
            )
        return qs

    @extend_schema(
        tags=['История операций'],
        summary='Траты за текущий и будущий месяц и по параметрам',
        responses={status.HTTP_200_OK: InfoTransactionSerializator()},
        parameters=[
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Дата начала периода (формат: YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Дата окончания периода (формат: YYYY-MM-DD)'
            ),
            OpenApiParameter(
                name='month',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Месяц'
            ),
            OpenApiParameter(
                name='year',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Год'
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def info(self, request, *args, **kwargs):
        """
        Возвращает информацию о сумме транзакций
        пользователя за определенный период.

        Возвращает:
        - total_next_month (int): Общая сумма списаний пользователя
        за следующий месяц.
        - total_current_month (int): Общая сумма списаний пользователя
        за текущий месяц.
        - total_param (int): Общая сумма списаний пользователя
        с учетом параметров фильтрации.
        - total_cashback (int): Сумма транзакций кешбека пользователя
        с 25 числа прошлого месяца до 25 числа текущего месяца.
        """
        queryset_filtered = self.filter_queryset(self.get_queryset()).filter(
            transaction_type='DEBIT'
        )
        queryset = self.get_queryset().filter(transaction_type='DEBIT')

        current_date = timezone.now()
        next_month_date = current_date + relativedelta(months=1)

        start_date, end_date = get_cashback_transactions_period()
        queryset_cashback = self.get_queryset().filter(
            transaction_date__gte=start_date,
            transaction_date__lte=end_date,
            transaction_type='DEBIT'
        )

        totals = get_transaction_totals(
            queryset_filtered,
            queryset,
            queryset_cashback,
            current_date,
            next_month_date
        )

        serializer = InfoTransactionSerializator(totals)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # def dispatch(self, request, *args, **kwargs):
    #     res = super().dispatch(request, *args, **kwargs)
    #     from django.db import connection
    #     print(len(connection.queries))
    #     for q in connection.queries:
    #         print('>>>>>>', q['sql'])
    #     return res
