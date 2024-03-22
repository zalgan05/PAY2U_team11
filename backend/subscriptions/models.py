import math
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()

MAX_LEGTH = 64


class Subscription(models.Model):
    """Модель сервиса подписки."""

    CHOICES_TYPE = (
        ('film', 'Кино'),
        ('music', 'Музыка'),
        ('book', 'Книги'),
        ('other', 'Другое'),
    )

    name = models.CharField(max_length=MAX_LEGTH)
    description = models.TextField()
    type = models.CharField(
        max_length=MAX_LEGTH,
        choices=CHOICES_TYPE
    )
    cashback = models.IntegerField()

    class Meta:
        verbose_name = 'Сервис подписки'
        verbose_name_plural = 'Сервисы подписок'

    def __str__(self):
        return f'{self.name}'


class Tariff(models.Model):
    """Модель тарифа сервиса подписки."""

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='tariffs'
    )
    duration = models.IntegerField()
    price = models.IntegerField()
    discount = models.IntegerField()
    price_per_month = models.IntegerField(
        null=True,
        blank=True
    )
    price_per_duration = models.IntegerField(
        null=True,
        blank=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.price_per_month = self.calculate_price_per_month()
        self.price_per_duration = self.calculate_price_per_duration()

    def calculate_price_per_month(self):
        """Вычисляет стоимость подписки в месяц с учетом скидки."""
        if self.discount is not None:
            discount_rate = 1 - self.discount / 100
            return math.floor(self.price * discount_rate / 10 + 0.5) * 10
        else:
            return None

    def calculate_price_per_duration(self):
        """Вычисляет стоимость подписки за всю указанную длительность."""
        if self.duration is not None:
            return self.price_per_month * self.duration
        return None

    def save(self, *args, **kwargs):
        self.price_per_month = self.calculate_price_per_month()
        self.price_per_duration = self.calculate_price_per_duration()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Тариф подписки'
        verbose_name_plural = 'Тарифы подписок'

    def __str__(self):
        if self.duration == 1:
            return f'{self.duration} месяц сервиса {self.subscription.name}'
        elif self.duration in [2, 3, 4]:
            return f'{self.duration} месяца сервиса {self.subscription.name}'
        else:
            return f'{self.duration} месяцев сервиса {self.subscription.name}'


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

    name_subscriber = models.CharField(max_length=MAX_LEGTH)
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
