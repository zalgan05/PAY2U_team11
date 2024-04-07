import logging

from celery import shared_task
from celery.schedules import crontab
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from subscriptions.models import SubscriptionUserOrder, Transaction

from backend.celery import app as celery_app

from .services import current_transaction, future_transaction

User = get_user_model()
TEST_CELERY = settings.TEST_CELERY
celery_logger = logging.getLogger('celery')


@shared_task
def next_bank_transaction(order_id):
    """Задача для обработки следующей банковской транзакции."""
    try:
        celery_logger.info(
            f'Начало выполнения транзакции списания по заказу {order_id}'
        )
        order = SubscriptionUserOrder.objects.get(id=order_id)
        user = order.user
        price = order.tariff.price_per_period
        cashback = order.subscription.cashback
        with transaction.atomic():
            user.balance -= price
            user.save(update_fields=['balance'])
            trans = Transaction.objects.get(
                user=user,
                order=order,
                transaction_type='DEBIT',
                status='PENDING',
            )
            trans.status = 'PAID'
            trans.save()
        current_transaction(user, order, price, cashback)
        new_due_date = timezone.now() + relativedelta(
            months=order.tariff.period
        )
        order.due_date = new_due_date
        future_transaction(user, order, price)

        if TEST_CELERY:
            task = next_bank_transaction.apply_async(
                args=[order_id], eta=timezone.now() + relativedelta(seconds=10)
            )
        else:
            task = next_bank_transaction.apply_async(
                args=[order_id], eta=new_due_date
            )
        order.task_id_celery = task.id
        order.save()
        celery_logger.info(
            f'Успешная транзакции списания по заказу {order_id}'
        )

    except Exception as e:
        celery_logger.error(
            f'Ошибка при попытке списания по заказу {order_id}: {e}'
        )
        order.pay_status = False
        order.save()


@shared_task
def cancel_subscription_order(order_id):
    """
    Обновляет статус оплаты
    и дату следующего списания при отмене подписки
    """
    try:
        celery_logger.info(
            f'Начало выполнения обновления статуса оплаты и '
            f'даты следующего списания по заказу {order_id} после отмены'
        )
        order = SubscriptionUserOrder.objects.get(id=order_id)
        order.pay_status = False
        order.due_date = None
        order.save()
        celery_logger.info(
            f'Успешное выполнение обновления статуса оплаты и '
            f'даты следующего списания по заказу {order_id} после отмены'
        )
    except Exception as e:
        celery_logger.error(
            f'Ошибка при отмене обновления статуса оплаты и '
            f'даты следующего списания по заказу {order_id}: {e}'
        )


@shared_task
def pay_cashback():
    """Выполняет выплату кешбека пользователям."""
    try:
        celery_logger.info(f'Начало выплат кешбека {timezone.now}')
        transactions = (
            Transaction.objects.filter(
                transaction_type='CASHBACK',
                status='PENDING',
            )
            .values('user')
            .annotate(total_cashback=Sum('amount'))
        )

        for transaction_data in transactions:
            user = User.objects.get(id=transaction_data['user'])
            cashback_amount = transaction_data['total_cashback']

            with transaction.atomic():
                user.balance += cashback_amount
                user.save(update_fields=['balance'])
                transactions.filter(user=user).update(status='CREDITED')
        celery_logger.info(f'Весь кешбек успешно выплачен {timezone.now}')
    except Exception as e:
        celery_logger.info(f'При выплате кешбека произошла ошибка: {e}')


if TEST_CELERY:
    from datetime import timedelta

    celery_app.conf.beat_schedule = {
        'pay_cashback': {
            'task': 'api.v1.tasks.pay_cashback',
            'schedule': timedelta(seconds=30),
        },
    }
else:
    celery_app.conf.beat_schedule = {
        'pay_cashback': {
            'task': 'api.v1.tasks.pay_cashback',
            'schedule': crontab(day_of_month=25, hour=0, minute=0),
        },
    }
