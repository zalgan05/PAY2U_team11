from celery import shared_task
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta
from celery.schedules import crontab

from .services import current_transaction, future_transaction
from subscriptions.models import SubscriptionUserOrder, Transaction
from backend.celery import app as celery_app


User = get_user_model()


@shared_task
def next_bank_transaction(order_id):
    """Задача для обработки следующей банковской транзакции."""
    try:
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
                status='PENDING'
            )
            trans.status = 'PAID'
            trans.save()
        current_transaction(user, order, price, cashback)
        new_due_date = (
            timezone.now() + relativedelta(months=order.tariff.period)
        )
        order.due_date = new_due_date
        future_transaction(user, order, price)

        # Test
        task = next_bank_transaction.apply_async(
            args=[order_id], eta=timezone.now() + relativedelta(seconds=10)
        )

        # task = next_bank_transaction.apply_async(
        #     args=[order_id], eta=new_due_date
        # )
        order.task_id_celery = task.id
        order.save()

    except Exception as e:
        print(e)
        order.pay_status = False
        order.save()


@shared_task
def update_pay_status_and_due_date(order_id):
    """Задача для обновления статуса оплаты и даты следующего списания."""
    order = SubscriptionUserOrder.objects.get(id=order_id)
    order.pay_status = False
    order.due_date = None
    order.save()


@shared_task
def pay_cashback():
    try:
        transactions = Transaction.objects.filter(
            transaction_type='CASHBACK',
            status='PENDING',
        ).values('user').annotate(total_cashback=Sum('amount'))

        for transaction_data in transactions:
            user = User.objects.get(id=transaction_data['user'])
            cashback_amount = transaction_data['total_cashback']

            with transaction.atomic():
                user.balance += cashback_amount
                user.save(update_fields=['balance'])
                transactions.filter(user=user).update(status='CREDITED')
    except Exception as e:
        print(e)

    print('<<<<<<<<<<<<ВСЕ КЕШБЕКИ ВЫПЛАЧЕНЫ>>>>>>>>>>>>')


# from datetime import timedelta
celery_app.conf.beat_schedule = {
    'pay_cashback': {
        'task': 'api.v1.tasks.pay_cashback',
        # 'schedule': timedelta(seconds=30),
        'schedule': crontab(day_of_month=25, hour=0, minute=0),
    },
}
