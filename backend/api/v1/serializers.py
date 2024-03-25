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

    class Meta:
        model = Subscription
        fields = ['id', 'name', 'description', 'type', 'cashback', 'min_price']

    def get_min_price(self, obj) -> int:
        return obj.tariffs.first().price_per_month


class SubscriptionDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детального представления модели Subscription."""

    tariffs = TariffSerializer(many=True)

    class Meta:
        model = Subscription
        fields = ['id', 'name', 'description', 'type', 'cashback', 'tariffs']


class IsFavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления и удаления подписки в избранное."""

    class Meta:
        model = Subscription
        fields = ['id',]
        read_only_fields = ['id',]

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
                return super().validate(attrs)
        return super().validate(attrs)

    def create(self, validated_data):
        """
        Создает связь пользователя с подпиской и добавляет ее в избранное.
        """
        sub_id = self.context.get('sub_id')
        subscription = get_object_or_404(Subscription, id=sub_id)
        IsFavoriteSubscription.objects.create(
            user=User,
            subscription=subscription
        )
        return subscription
