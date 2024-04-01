from celery import shared_task
from django.db import transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from subscriptions.models import SubscriptionUserOrder


@shared_task
def next_bank_transaction(order_id):
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
        order.save()
        # return next_bank_transaction.apply_async(
        #     args=[order_id], eta=timezone.now() + relativedelta(seconds=10)
        # )
        return next_bank_transaction.apply_async(
            args=[order_id], eta=new_due_date
        )

    except Exception:
        order.pay_status = False
        order.save()
