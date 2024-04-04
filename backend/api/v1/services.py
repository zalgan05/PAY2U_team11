from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from dateutil.relativedelta import relativedelta

from subscriptions.models import Transaction


def bank_operation(user, subscription, tariff, subscription_order):
    """Симулирует банковскую операцию."""
    price = tariff.price_per_period
    cashback = subscription.cashback

    if user.balance < price:
        raise serializers.ValidationError('Недостаточно средств на счету.')

    try:
        with transaction.atomic():
            user.balance -= price
            user.save(update_fields=['balance'])

            current_transaction(user, subscription_order, price, cashback)
            future_transaction(user, subscription_order, price)

    except Exception:
        raise serializers.ValidationError(
            'Ошибка при выполнении банковской операции. '
            'Проверьте данные и повторите попытку.'
        )


def current_transaction(user, subscription_order, price, cashback):
    """
    Создает запись о текущей транзакции списания пользователя и
    создает будущую транзакцию начисления кэшбэка.

    Args:
        user: Пользователь, выполняющий транзакцию.
        subscription_order: Заказ подписки,
        для которого выполняется транзакция.
        price: Сумма транзакции.
        cashback: Процент кэшбэка.
    """
    Transaction.objects.create(
        user=user,
        order=subscription_order,
        amount=price,
        transaction_type='DEBIT',
        transaction_date=timezone.now(),
        status='PAID'
    )
    cashback = price * cashback // 100
    Transaction.objects.create(
        user=user,
        order=subscription_order,
        amount=cashback,
        transaction_type='CASHBACK',
        transaction_date=timezone.now(),
        status='PENDING'
    )


def future_transaction(user, subscription_order, price):
    """
    Создает запись о будущей транзакции списания пользователя.

    Args:
        user: Пользователь, выполняющий транзакцию.
        subscription_order: Заказ подписки,
        для которого выполняется транзакция.
        price: Сумма транзакции.
    """
    Transaction.objects.create(
        user=user,
        order=subscription_order,
        amount=price,
        transaction_type='DEBIT',
        transaction_date=subscription_order.due_date,
        status='PENDING'
    )


def get_cashback_transactions_period():
    """
    Возвращает начальную и конечную даты периода
    для расчета транзакций кешбека.
    """
    today = timezone.now().replace(hour=23, minute=59, second=59)
    last_month = today - relativedelta(months=1)
    start_date = last_month.replace(day=25)
    end_date = today.replace(day=25)
    return start_date, end_date


def get_transaction_totals(
        queryset_filtered,
        queryset,
        queryset_cashback,
        current_date,
        next_month_date
):
    """
    Вычисляет общие суммы транзакций для различных категорий.

    Аргументы:
    - queryset_filtered (QuerySet): Фильтрованный QuerySet для транзакций списания.
    - queryset (QuerySet): QuerySet транзакций списания.
    - queryset_cashback (QuerySet): QuerySet транзакций кешбека.
    - current_date (datetime): Текущая дата.
    - next_month_date (datetime): Дата следующего месяца.

    Возвращает:
    - total_current_month (int): Общая сумма транзакций списания пользователя за текущий месяц.
    - total_next_month (int): Общая сумма транзакций списания пользователя за следующий месяц.
    - total_param (int): Общая сумма транзакций списания пользователя с учетом параметров фильтрации.
    - total_cashback (int): Сумма транзакций кешбека пользователя за указанный период.
    # noqa
    """
    total_param = queryset_filtered.aggregate(
        total_param=Sum('amount')
    )['total_param']

    total_next_month = queryset.filter(
        transaction_date__month=next_month_date.month
    ).aggregate(total_next_month=Sum('amount'))['total_next_month']

    total_current_month = queryset.filter(
        transaction_date__month=current_date.month
    ).aggregate(total_current_month=Sum('amount'))['total_current_month']

    total_cashback = queryset_cashback.aggregate(
        total_cashback=Sum('amount')
    )['total_cashback']

    return {
        'total_current_month': total_current_month,
        'total_next_month': total_next_month,
        'total_param': total_param,
        'total_cashback': total_cashback
    }
