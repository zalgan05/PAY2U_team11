from celery import shared_task
from django.db import transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from subscriptions.models import SubscriptionUserOrder


@shared_task
def next_bank_transaction(order_id):
    """Задача для обработки следующей банковской транзакции."""
    try:
        order = SubscriptionUserOrder.objects.get(id=order_id)
        user = order.user
        with transaction.atomic():
            user.balance -= order.tariff.price
            user.save(update_fields=['balance'])
        new_due_date = (
            timezone.now() + relativedelta(months=order.tariff.period)
        )
        order.due_date = new_due_date
        # task = next_bank_transaction.apply_async(
        #     args=[order_id], eta=timezone.now() + relativedelta(seconds=10)
        # )
        task = next_bank_transaction.apply_async(
            args=[order_id], eta=new_due_date
        )
        order.task_id_celery = task.id
        order.save()

    except Exception:
        order.pay_status = False
        order.save()


@shared_task
def update_pay_status_and_due_date(order_id):
    """Задача для обновления статуса оплаты и даты следующего списания."""
    order = SubscriptionUserOrder.objects.get(id=order_id)
    order.pay_status = False
    order.due_date = None
    order.save()
