from django.contrib import admin

from subscriptions.models import (
    Subscription,
    Tariff,
    SubscriptionUserOrder,
    IsFavoriteSubscription
)


class LinkInlines(admin.StackedInline):
    model = Tariff
    extra = 1
    fields = (
        'duration',
        'price',
        'discount'
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    inlines = [LinkInlines,]
    list_display = (
        'name',
        'description',
        'type',
    )


@admin.register(Tariff)
class TariffnAdmin(admin.ModelAdmin):
    list_display = (
        'subscription',
        'duration',
        'price',
        'discount'
    )
    fields = (
        'subscription',
        'duration',
        'price',
        'discount'
    )


@admin.register(SubscriptionUserOrder)
class SubscriptionUserOrderAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'subscription',
        'tariff',
        'status'
    )


@admin.register(IsFavoriteSubscription)
class IsFavoriteSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'subscription',
    )
