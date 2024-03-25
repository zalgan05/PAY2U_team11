from rest_framework import serializers

from subscriptions.models import Subscription, Tariff


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
