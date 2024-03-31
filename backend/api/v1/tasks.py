from celery import shared_task
from django.db import transaction
from django.utils import timezone

from subscriptions.models import SubscriptionUserOrder


@shared_task
def next_bank_transaction(order_id):
    try:
        order = SubscriptionUserOrder.objects.get(id=order_id)
        user = order.user
        with transaction.atomic():
            user.balance -= order.price
            user.save(update_fields=['balance'])
        new_due_date = timezone.now() + order.tariff.period
        order.due_date = new_due_date
        next_bank_transaction.apply_async(
            args=[order_id], eta=new_due_date
        )

    except Exception:
        order.pay_status = False
