from django_filters.rest_framework import BooleanFilter, FilterSet

from subscriptions.models import Subscription


class SubscriptionFilter(FilterSet):

    is_favorited = BooleanFilter(method='get_is_favorited')

    class Meta:
        model = Subscription
        fields = ('is_favorited',)

    def get_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated:
            if value:
                return queryset.filter(is_favorite__user=self.request.user)
            return queryset.exclude(is_favorite__user=self.request.user)
        return queryset
