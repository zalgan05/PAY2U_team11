from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from subscriptions.models import Tariff, Transaction


def bank_operation(context, validated_data, subscription_order):
    """Симулирует банковскую операцию."""
    user = context['request'].user
    tariff_id = validated_data['tariff'].id
    price = Tariff.objects.get(id=tariff_id).price_per_period

    if user.balance < price:
        raise serializers.ValidationError('Недостаточно средств на счету.')

    try:
        with transaction.atomic():
            user.balance -= price
            user.save(update_fields=['balance'])

            current_transaction(user, subscription_order, price)
            future_transaction(user, subscription_order, price)

    except Exception:
        raise serializers.ValidationError(
            'Ошибка при выполнении банковской операции. '
            'Проверьте данные и повторите попытку.'
        )


def current_transaction(user, subscription_order, price):
    Transaction.objects.create(
        user=user,
        order=subscription_order,
        amount=price,
        transaction_type='DEBIT',
        transaction_date=timezone.now(),
        status='PAID'
    )
    Transaction.objects.create(
        user=user,
        order=subscription_order,
        amount=price,
        transaction_type='CASHBACK',
        transaction_date=timezone.now(),
        status='PENDING'
    )


def future_transaction(user, subscription_order, price):
    Transaction.objects.create(
        user=user,
        order=subscription_order,
        amount=price,
        transaction_type='DEBIT',
        transaction_date=subscription_order.due_date,
        status='PENDING'
    )
