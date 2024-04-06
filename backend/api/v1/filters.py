from django.db.models import Q
from django_filters.rest_framework import (
    BooleanFilter,
    CharFilter,
    DateFilter,
    FilterSet,
    NumberFilter,
)
from subscriptions.models import Subscription, Transaction


class CaseInsensitiveStartsWithCharFilter(CharFilter):
    """
    Фильтр для поиска строк, начинающихся с указанного значения,
    с учетом регистра символов.
    """

    def filter(self, qs, value):
        if value:
            return qs.filter(
                Q(**{f'{self.field_name}__istartswith': value})
                | Q(**{f'{self.field_name}__istartswith': value.capitalize()})
            )
        return qs


class SubscriptionFilter(FilterSet):
    """
    Фильтр для подписок с возможностью поиска по категории, имени
    и установленному флагу "избранное" для текущего пользователя.
    """

    name = CaseInsensitiveStartsWithCharFilter(field_name='name')
    category = CharFilter(field_name='categories__slug')
    is_favorite = BooleanFilter(method='get_is_favorite')

    class Meta:
        model = Subscription
        fields = ('is_favorite', 'name', 'category')

    def get_is_favorite(self, queryset, name, value):
        if self.request.user.is_authenticated:
            if value:
                return queryset.filter(is_favorite__user=self.request.user)
            return queryset.exclude(is_favorite__user=self.request.user)
        return queryset


class HistoryFilter(FilterSet):
    """
    Фильтр для транзакций с возможностью поиска по году, месяцу
    и диапазону дат.
    """

    year = NumberFilter(field_name='transaction_date__year')
    month = NumberFilter(field_name='transaction_date__month')
    start_date = DateFilter(field_name='transaction_date', lookup_expr='gte')
    end_date = DateFilter(field_name='transaction_date', lookup_expr='lte')

    class Meta:
        model = Transaction
        fields = ('year', 'month', 'start_date', 'end_date')
