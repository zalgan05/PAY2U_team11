from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from subscriptions.models import Subscription, Tariff, IsFavoriteSubscription

User = get_user_model()


class TariffSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tariff."""

    class Meta:
        model = Tariff
        exclude = ['subscription', 'price']


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Subscription."""

    min_price = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            'id',
            'name',
            'description',
            'type',
            'cashback',
            'min_price',
            'is_favorited'
        ]

    def get_min_price(self, obj) -> int:
        """Возвращает минимальную цену подписки."""
        return obj.tariffs.first().price_per_month

    def get_is_favorited(self, obj) -> bool:
        """Проверяет, добавлен ли сервис в избранное для пользователя."""
        user = self.context.get('request').user
        if self.context.get('request').user.is_authenticated:
            return obj.is_favorite.filter(user=user).exists()
        return False


class SubscriptionDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детального представления модели Subscription."""

    tariffs = TariffSerializer(many=True)

    class Meta:
        model = Subscription
        fields = ['id', 'name', 'description', 'type', 'cashback', 'tariffs']


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
