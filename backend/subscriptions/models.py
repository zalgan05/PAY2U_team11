import math
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

MAX_LEGTH = 64


class Subscription(models.Model):
    """Модель сервиса подписки."""

    CHOICES_TYPE = (
        ('film', 'Кино')
        ('music', 'Музыка')
        ('book', 'Книги')
        ('other', 'Другое')
    )

    name = models.CharField(max_length=MAX_LEGTH)
    description = models.TextField()
    type = models.CharField(choices=CHOICES_TYPE)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.price_per_month = self.calculate_price_per_month()
        self.price_per_duration = self.calculate_price_per_duration()

    def calculate_price_per_month(self):
        """Вычисляет стоимость подписки в месяц с учетом скидки."""
        discount_rate = 1 - self.discount / 100
        return math.floor(self.price * discount_rate * 10) / 10

    def calculate_price_per_duration(self):
        """Вычисляет стоимость подписки за всю указанную длительность."""
        return math.floor(self.price_per_month * self.duration * 10) / 10

    class Meta:
        verbose_name = 'Тариф подписки'
        verbose_name_plural = 'Тарифы подписок'


class SubscriptionOrder(models.Model):
    # user = models.ForeignKey(
    #     User,
    #     on_delete=models.CASCADE,
    #     related_name='user_order'
    # )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='subscription_order'
    )
    name_subscriber = models.CharField(max_length=MAX_LEGTH)
    phone_number = models.ImageField()
    email = models.EmailField()
    tariff = models.ForeignKey(
        Tariff,
        on_delete=models.CASCADE,
        related_name='tariff_order'
    )


class SubscriptionUser(models.Model):
    """Модель связи подписка-пользователь."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order = models.ForeignKey(
        SubscriptionOrder,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    status = models.BooleanField(defaul=False)
