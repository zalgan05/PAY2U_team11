from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from drf_spectacular.utils import (
    # extend_schema,
    extend_schema_field,
    # extend_schema_view,
)
from dateutil.relativedelta import relativedelta

# from .tasks import (
#     next_bank_transaction,
#     update_pay_status_and_due_date
# )
from subscriptions.models import (
    BannersSubscription,
    CategorySubscription,
    Subscription,
    Tariff,
    IsFavoriteSubscription,
    SubscriptionUserOrder
)

User = get_user_model()


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
    """Сериализатор для модели Subscription."""

    # min_price = serializers.SerializerMethodField()
    min_price = serializers.IntegerField()
    is_favorite = serializers.SerializerMethodField()
    categories = CategorySubscriptionSerializer(many=True)

    class Meta:
        model = Subscription
        fields = [
            'id',
            'name',
            'logo',
            'description',
            'categories',
            'cashback',
            'popular_rate',
            'min_price',
            'is_favorite'
        ]

    # def get_min_price(self, obj) -> int:
    #     """Возвращает минимальную цену подписки."""
    #     return obj.tariffs.first().price_per_month

    def get_is_favorite(self, obj) -> bool:
        """Проверяет, добавлен ли сервис в избранное для пользователя."""
        user = self.context.get('request').user
        if self.context.get('request').user.is_authenticated:
            return obj.is_favorite.filter(user=user).exists()
        return False


class SubscriptionDetailSerializer(SubscriptionSerializer):
    """Сериализатор для детального представления модели Subscription."""

    # tariffs = TariffSerializer(many=True)
    banners = BannersSubscriptionSerializer(many=True)

    class Meta(SubscriptionSerializer.Meta):
        fields = list(SubscriptionSerializer.Meta.fields)
        fields.remove('min_price')
        fields += [
            # 'tariffs',
            'title',
            'banners'
        ]

# class SubscriptionDetailSerializer(serializers.ModelSerializer):
#     """Сериализатор для детального представления модели Subscription."""

#     tariffs = TariffSerializer(many=True)
#     category = CategorySubscriptionSerializer(many=True)

#     class Meta:
#         model = Subscription
#         fields = [
#             'id',
#             'name',
#             'description',
#             'category',
#             'cashback',
#             'tariffs'
#         ]


class SubscriptionOrderSerializer(serializers.ModelSerializer):
    """Сериализатор для создания заказа подписки."""

    class Meta:
        model = SubscriptionUserOrder
        fields = ['name', 'phone_number', 'email', 'tariff', 'due_date']
        read_only_fields = ['due_date',]

    def create(self, validated_data):
        try:
            with transaction.atomic():
                self.bank_operation(validated_data)
                tariff = validated_data['tariff']
                validated_data['due_date'] = (
                    timezone.now() + relativedelta(months=(tariff.period))
                )
                subscription_order = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                'У пользователя уже существует подписка на этот сервис.'
            )
        except Exception:
            raise serializers.ValidationError(
                'Ошибка при выполнении создании подписки. '
                'Повторите попытку.'
            )
        return subscription_order

    def bank_operation(self, validated_data):
        """Симулирует банковскую операцию."""
        user = self.context['request'].user
        tariff_id = validated_data['tariff'].id
        price = Tariff.objects.get(id=tariff_id).price_per_period

        if user.balance < price:
            raise serializers.ValidationError('Недостаточно средств на счету.')

        try:
            with transaction.atomic():
                user.balance -= price
                user.save(update_fields=['balance'])

        except Exception:
            raise serializers.ValidationError(
                'Ошибка при выполнении банковской операции. '
                'Проверьте данные и повторите попытку.'
            )

    def validate_tariff(self, value):
        """Валидирует выбранный тариф подписки."""
        sub_id = self.context['sub_id']
        if value.subscription.id != int(sub_id):
            raise serializers.ValidationError(
                'Выбранный тариф не принадлежит указанному сервису подписки.'
            )
        return value


class MyTariffUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления тарифа подписки пользователя."""

    class Meta:
        model = SubscriptionUserOrder
        fields = ['tariff',]

    def update(self, instance, validated_data):
        instance.tariff = validated_data['tariff']
        instance.save()
        return instance

    def validate_tariff(self, value):
        if (
            not self.context['subscription']
            .tariffs.filter(id=value.id).exists()
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
                user=user,
                subscription=subscription
            ).exists():
                raise serializers.ValidationError(
                    'Вы уже добавили сервис в избранное'
                )
        elif request.method == 'DELETE':
            if not IsFavoriteSubscription.objects.filter(
                user=user,
                subscription=subscription
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
            user=self.context['request'].user,
            subscription=subscription
        )


class MySubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Subscription для использования в представлении my
    для отображения подписок пользователя.
    Включает информацию о тарифе и статусе оплаты.
    """

    tariff = serializers.SerializerMethodField()
    pay_status = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            'id',
            'name',
            'logo',
            'cashback',
            'tariff',
            'pay_status'
        )

    @extend_schema_field(field=TariffSerializer())
    def get_tariff(self, obj) -> dict:
        tariff = obj.orders.select_related('tariff').get().tariff
        return TariffSerializer(tariff).data

    def get_pay_status(self, obj) -> bool:
        return obj.orders.get().pay_status
