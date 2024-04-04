from django.contrib import admin

from subscriptions.models import (
    BannersSubscription,
    CategorySubscription,
    Subscription,
    Tariff,
    SubscriptionUserOrder,
    IsFavoriteSubscription,
    Transaction,
)


class LinkInlines(admin.StackedInline):
    model = Tariff
    extra = 1
    fields = (
        'period',
        'price',
        'discount'
    )


class BannersInlines(admin.StackedInline):
    model = BannersSubscription
    extra = 1
    fields = (
        'image',
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    inlines = [LinkInlines, BannersInlines]
    list_display = (
        'name',
        'title',
        'description',
        'categories_list',
    )

    @admin.display(description='Категории')
    def categories_list(self, row):
        return ','.join([x.name for x in row.categories.all()])


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'subscription',
        'period',
        'price',
        'discount',
        'price_per_period',
        'slug'
    )
    fields = (
        'subscription',
        'period',
        'price',
        'discount'
    )
    list_filter = (
        'subscription',
        'period',
    )


@admin.register(SubscriptionUserOrder)
class SubscriptionUserOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'subscription',
        'tariff',
        'pay_status'
    )


@admin.register(IsFavoriteSubscription)
class IsFavoriteSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'subscription',
    )


@admin.register(CategorySubscription)
class CategorySubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'order',
        'transaction_type',
        'transaction_date',
        'amount',
        'status'
    )
    list_filter = (
        'user',
        'status',
        'transaction_type'
    )
