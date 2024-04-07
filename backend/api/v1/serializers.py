import logging

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from subscriptions.models import (
    BannersSubscription,
    CategorySubscription,
    IsFavoriteSubscription,
    Subscription,
    SubscriptionUserOrder,
    Tariff,
    Transaction,
)

from .services import bank_operation

User = get_user_model()
client_logger = logging.getLogger('client')


class CategorySubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для модели категории сервиса подписки."""

    class Meta:
        model = CategorySubscription
        fields = '__all__'


class BannersSubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для картинок баннера сервиса подписки."""

    class Meta:
        model = BannersSubscription
        fields = ['id', 'image']


class TariffSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tariff."""

    class Meta:
        model = Tariff
        exclude = ['subscription', 'price']


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Subscription.

    Поля:
    - id (int): Идентификатор подписки.
    - name (str): Название подписки.
    - logo (str): URL-адрес логотипа подписки.
    - cashback (int): Процент кешбэка для подписки.
    """

    class Meta:
        model = Subscription
        fields = (
            'id',
            'name',
            'logo',
            'cashback',
        )


class SubscriptionCatalogSerializer(SubscriptionSerializer):
    """
    Сериализатор для модели Subscription, используемый в каталоге подписок.

    Дополнительные поля:
    - description (str): Описание подписки.
    - categories (list): Список категорий подписки.
    - popular_rate (float): Рейтинг популярности подписки.
    - min_price (int): Минимальная цена подписки.
    - is_favorite (bool): Флаг, указывающий, добавлена ли подписка в избранное
      для пользователя.
    """

    min_price = serializers.IntegerField()
    is_favorite = serializers.SerializerMethodField()
    categories = CategorySubscriptionSerializer(many=True)

    class Meta(SubscriptionSerializer.Meta):
        fields = SubscriptionSerializer.Meta.fields + (
            'description',
            'categories',
            'popular_rate',
            'min_price',
            'is_favorite',
        )

    def get_is_favorite(self, obj) -> bool:
        """Проверяет, добавлен ли сервис в избранное для пользователя."""
        user = self.context.get('request').user
        if self.context.get('request').user.is_authenticated:
            return obj.is_favorite.filter(user=user).exists()
        return False


class SubscriptionDetailSerializer(SubscriptionCatalogSerializer):
    """
    Сериализатор для детального представления модели Subscription.

    Дополнительные поля:
    - title (str): Подзаголовок подписки.
    - banners (list): Список URL-адресов баннеров (картинок) для подписки.
    """

    banners = BannersSubscriptionSerializer(many=True)

    class Meta(SubscriptionCatalogSerializer.Meta):
        fields = list(SubscriptionCatalogSerializer.Meta.fields)
        fields.remove('min_price')
        fields += ['title', 'banners']


class SubscriptionOrderSerializer(serializers.ModelSerializer):
    """Сериализатор для создания заказа подписки."""

    class Meta:
        model = SubscriptionUserOrder
        fields = ['name', 'phone_number', 'email', 'tariff', 'due_date']
        read_only_fields = [
            'due_date',
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        sub_id = self.context['sub_id']
        subscription = get_object_or_404(Subscription, id=sub_id)
        tariff = validated_data['tariff']
        due_date = timezone.now() + relativedelta(months=(tariff.period))
        try:
            with transaction.atomic():
                validated_data['due_date'] = due_date
                subscription_order = super().create(validated_data)
                bank_operation(user, subscription, tariff, subscription_order)
        except IntegrityError:
            raise serializers.ValidationError(
                'У пользователя уже существует подписка на этот сервис.'
            )
        except Exception as e:
            client_logger.error(
                f'У пользователя {user.id} возникла ошибка {e}'
                f'при попытке подписаться на {subscription.id}'
            )
            raise serializers.ValidationError(
                'Ошибка при выполнении создании подписки. '
                'Повторите попытку.'
            )
        return subscription_order

    def validate_tariff(self, value):
        """Валидирует выбранный тариф подписки."""
        sub_id = self.context['sub_id']
        if value.subscription.id != int(sub_id):
            raise serializers.ValidationError(
                'Выбранный тариф не принадлежит указанному сервису подписки.'
            )
        return value


class MyTariffSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели SubscriptionUserOrder, представляющий
    информацию о тарифе подписки.

    Поля:
    - id (int): Уникальный идентификатор тарифа.
    - price_per_period (int): Цена за период тарифа.
    - slug (str): Уникальный идентификатор тарифа.
    - due_date (date): Дата слеюущего списания средств.
    - cashback (int): Рассчитанная сумма кэшбэка от стоимости тарифа.

    Методы:
    - get_cashback: Метод для рассчета суммы кэшбэка на основе
    цены тарифа и процента кэшбэка.
    """

    id = serializers.IntegerField(source='tariff.id')
    price_per_period = serializers.IntegerField(
        source='tariff.price_per_period'
    )
    slug = serializers.SlugField(source='tariff.slug')
    cashback = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionUserOrder
        fields = ('id', 'price_per_period', 'slug', 'due_date', 'cashback')

    def get_cashback(self, obj) -> int:
        cashback = obj.subscription.cashback
        price_per_period = obj.tariff.price_per_period
        return price_per_period * cashback // 100


class MyTariffUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления тарифа подписки пользователя."""

    class Meta:
        model = SubscriptionUserOrder
        fields = [
            'tariff',
        ]

    def update(self, instance, validated_data):
        instance.tariff = validated_data['tariff']
        instance.save()
        return instance

    def validate_tariff(self, value):
        if (
            not self.context['subscription']
            .tariffs.filter(id=value.id)
            .exists()
        ):
            raise serializers.ValidationError(
                'Выбранный тариф не принадлежит указанной подписке'
            )
        return value


class IsFavoriteSerializer(serializers.Serializer):
    """Сериализатор для добавления и удаления подписки в избранное."""

    def validate(self, attrs):
        """
        Проверяет, добавлена ли подписка в избранное для текущего пользователя,
        и удаляет ее в зависимости от запроса.
        """
        request = self.context.get('request')
        user = request.user
        sub_id = self.context.get('sub_id')
        subscription = get_object_or_404(Subscription, id=sub_id)

        if request.method == 'POST':
            if IsFavoriteSubscription.objects.filter(
                user=user, subscription=subscription
            ).exists():
                raise serializers.ValidationError(
                    'Вы уже добавили сервис в избранное'
                )
        elif request.method == 'DELETE':
            if not IsFavoriteSubscription.objects.filter(
                user=user, subscription=subscription
            ).exists():
                raise serializers.ValidationError(
                    'Вы не добавляли этот сервис в избранное'
                )
            else:
                IsFavoriteSubscription.objects.filter(
                    user=user, subscription=subscription
                ).delete()
                return attrs
        return attrs

    def save(self, **kwargs):
        """
        Создает связь пользователя с подпиской и добавляет ее в избранное.
        """
        sub_id = self.context.get('sub_id')
        subscription = get_object_or_404(Subscription, id=sub_id)
        IsFavoriteSubscription.objects.create(
            user=self.context['request'].user, subscription=subscription
        )


class MySubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели SubscriptionUserOrder для использования
    в представлении my для отображения подписок пользователя.

    Поля:
    - id (int): Идентификатор подписки пользователя.
    - name (str): Название подписки пользователя.
    - logo (str): URL-адрес логотипа подписки пользователя.
    - cashback (int): Процент кешбэка для подписки пользователя.
    - tariff (dict): Информация о тарифе подписки пользователя.
    - pay_status (str): Статус оплаты подписки пользователя.
    - due_date (date): Дата окончания подписки пользователя.
    """

    tariff = TariffSerializer()
    id = serializers.IntegerField(source='subscription.id')
    name = serializers.CharField(source='subscription.name')
    logo = serializers.ImageField(source='subscription.logo')
    cashback = serializers.IntegerField(source='subscription.cashback')

    class Meta:
        model = SubscriptionUserOrder
        fields = (
            'id',
            'name',
            'logo',
            'cashback',
            'tariff',
            'pay_status',
            'due_date',
        )


class SubscriptionForHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для подписок в истории транзакций."""

    categories = CategorySubscriptionSerializer(many=True)

    class Meta:
        model = Subscription
        fields = ('id', 'name', 'logo', 'categories')


class HistoryTransactionSerializator(serializers.ModelSerializer):
    """Сериализатор для транзакций в истории.."""

    subscription = SubscriptionForHistorySerializer(
        source='order.subscription'
    )
    tariff = serializers.ReadOnlyField(source='order.tariff.slug')

    class Meta:
        model = Transaction
        fields = (
            'id',
            'subscription',
            'tariff',
            'transaction_type',
            'transaction_date',
            'amount',
            'status',
        )


class InfoTransactionSerializator(serializers.Serializer):
    """Сериализатор для информации о суммах транзакциях."""

    total_next_month = serializers.IntegerField()
    total_current_month = serializers.IntegerField()
    total_param = serializers.IntegerField()
    total_cashback = serializers.IntegerField()
