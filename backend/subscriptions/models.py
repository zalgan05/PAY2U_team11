import math
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()

MAX_LENGTH = 64


class Subscription(models.Model):
    """Модель сервиса подписки."""

    name = models.CharField(max_length=MAX_LENGTH)
    description = models.TextField()
    categories = models.ManyToManyField(
        'CategorySubscription',
    )
    cashback = models.IntegerField()

    class Meta:
        verbose_name = 'Сервис подписки'
        verbose_name_plural = 'Сервисы подписок'

    def __str__(self):
        return f'{self.name}'


class CategorySubscription(models.Model):
    """Модель категории сервиса подписки."""

    name = models.CharField(max_length=MAX_LENGTH)
    slug = models.SlugField(max_length=MAX_LENGTH, unique=True)

    class Meta:
        verbose_name = 'Категория сервиса'
        verbose_name_plural = 'Категории сервисов'

    def __str__(self):
        return f'{self.name}'


class Tariff(models.Model):
    """Модель тарифа сервиса подписки."""

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='tariffs'
    )
    period = models.IntegerField()
    price = models.IntegerField()
    discount = models.IntegerField()
    price_per_month = models.IntegerField(
        null=True,
        blank=True
    )
    price_per_period = models.IntegerField(
        null=True,
        blank=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.price_per_month = self.calculate_price_per_month()
        self.price_per_period = self.calculate_price_per_period()

    def calculate_price_per_month(self):
        """Вычисляет стоимость подписки в месяц с учетом скидки."""
        if self.discount is not None:
            discount_rate = 1 - self.discount / 100
            return math.floor(self.price * discount_rate / 10 + 0.5) * 10
        else:
            return None

    def calculate_price_per_period(self):
        """Вычисляет стоимость подписки за всю указанную длительность."""
        if self.period is not None:
            return self.price_per_month * self.period
        return None

    def save(self, *args, **kwargs):
        self.price_per_month = self.calculate_price_per_month()
        self.price_per_period = self.calculate_price_per_period()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Тариф подписки'
        verbose_name_plural = 'Тарифы подписок'

    def __str__(self):
        if self.period == 1:
            return f'{self.period} месяц сервиса {self.subscription.name}'
        elif self.period in [2, 3, 4]:
            return f'{self.period} месяца сервиса {self.subscription.name}'
        else:
            return f'{self.period} месяцев сервиса {self.subscription.name}'


class UserSubscription(models.Model):
    """Абстрактная модель связи подписка-пользователь."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class SubscriptionUserOrder(UserSubscription):
    """Модель связи заказа подписка-пользователь."""

    name = models.CharField(max_length=MAX_LENGTH)
    phone_number = models.IntegerField()
    email = models.EmailField()
    tariff = models.ForeignKey(
        Tariff,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    status = models.BooleanField(default=True)

    class Meta:
        default_related_name = 'orders'
        verbose_name = 'Заказ пользователя'
        verbose_name_plural = 'Заказы пользователя'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'subscription'],
                name='unique_orders',
            )
        ]

    def clean(self):
        if self.subscription != self.tariff.subscription:
            raise ValidationError(
                'Выбранный тариф не принадлежит указанной подписке'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class IsFavoriteSubscription(UserSubscription):
    """Создает связь пользователь-подписка избранное"""

    class Meta:
        default_related_name = 'is_favorite'
        verbose_name = 'Подписка в избранном'
        verbose_name_plural = 'Подписки в избранном'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'subscription'],
                name='unique_isfavorite',
            )
        ]
