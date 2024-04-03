from subscriptions.models import Transaction


def get_transaction_queryset(user):
    return Transaction.objects.filter(user=user)


def get_filtered_transaction_queryset(
        queryset,
        start_date=None,
        end_date=None,
        month=None,
        year=None
):

    if start_date and end_date:
        queryset = queryset.filter(
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        )
    elif month and year:
        queryset = queryset.filter(
            transaction_date__month=month,
            transaction_date__year=year
        )
    return queryset
