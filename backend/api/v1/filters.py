from django_filters.rest_framework import BooleanFilter, FilterSet, CharFilter
from django.db.models import Q

from subscriptions.models import Subscription


class CaseInsensitiveStartsWithCharFilter(CharFilter):
    def filter(self, qs, value):
        if value:
            return qs.filter(
                Q(**{f'{self.field_name}__istartswith': value}) |
                Q(**{f'{self.field_name}__istartswith': value.capitalize()})
            )
        return qs


class SubscriptionFilter(FilterSet):

    name = CaseInsensitiveStartsWithCharFilter(field_name='name')
    categories = CharFilter(field_name='categories__slug')
    is_favorite = BooleanFilter(method='get_is_favorite')

    class Meta:
        model = Subscription
        fields = ('is_favorite', 'name', 'categories')

    def get_is_favorite(self, queryset, name, value):
        if self.request.user.is_authenticated:
            if value:
                return queryset.filter(is_favorite__user=self.request.user)
            return queryset.exclude(is_favorite__user=self.request.user)
        return queryset
