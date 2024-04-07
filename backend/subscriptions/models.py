import math

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

User = get_user_model()

MAX_LENGTH = 64
MAX_VALUE_POPULAR = 100


def subscription_images_path(instance, filename):
    """Возвращает путь для сохранения изображений проекта."""
    if hasattr(instance, 'subscription'):
        return f'subscriptions/{instance.subscription.name}/images/{filename}'
    return f'subscriptions/{instance.name}/images/{filename}'


class BannersSubscription(models.Model):
    """Модель для хранения картинок баннера проекта."""

    subscription = models.ForeignKey(
        'Subscription',
        on_delete=models.CASCADE,
        related_name='banners',
        verbose_name='Сервис подписки',
    )
    image = models.ImageField(
        upload_to=subscription_images_path, verbose_name='Картинка сервиса'
    )


class Subscription(models.Model):
    """Модель сервиса подписки."""

    name = models.CharField(max_length=MAX_LENGTH, verbose_name='Название')
    title = models.CharField(
        max_length=MAX_LENGTH, verbose_name='Краткое описание'
    )
    description = models.TextField(verbose_name='Детальное описание')
    logo = models.ImageField(
        upload_to=subscription_images_path, verbose_name='Логотип сервиса'
    )
    categories = models.ManyToManyField(
        'CategorySubscription', verbose_name='Категории'
    )
    cashback = models.PositiveIntegerField(verbose_name='Процент кешбека')
    popular_rate = models.PositiveIntegerField(
        validators=[
            MaxValueValidator(MAX_VALUE_POPULAR),
        ],
        verbose_name='Рейтинг популярности',
    )

    class Meta:
        verbose_name = 'Сервис подписки'
        verbose_name_plural = 'Сервисы подписок'

    def __str__(self):
        return f'{self.name}'


class CategorySubscription(models.Model):
    """Модель категории сервиса подписки."""

    name = models.CharField(
        max_length=MAX_LENGTH, unique=True, verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH, unique=True, verbose_name='Слаг категории'
    )

    class Meta:
        verbose_name = 'Категория сервиса'
        verbose_name_plural = 'Категории сервисов'

    def __str__(self):
        return f'{self.name}'


class Tariff(models.Model):
    """Модель тарифа сервиса подписки."""

    PERIOD_CHOICES = [
        (1, 1),
        (3, 3),
        (6, 6),
        (12, 12),
    ]

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='tariffs',
        verbose_name='Сервис подписки',
    )
    period = models.IntegerField(
        choices=PERIOD_CHOICES, verbose_name='Продолжительность подписки'
    )
    price = models.PositiveIntegerField(
        verbose_name='Стоимость за месяц без скидки'
    )
    discount = models.PositiveIntegerField(verbose_name='Скидка')
    price_per_month = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Стоимость за месяц с учетом скидки',
    )
    price_per_period = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Стоимость за весь период с учетом скидки',
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Слаг тарифа',
    )

    def get_slug(self):
        """Возвращает слаг в зависимости от выбранного периода."""
        period_slug_mapping = {
            1: 'monthly',
            3: 'quarterly',
            6: 'semiannually',
            12: 'annually',
        }
        return period_slug_mapping.get(self.period)

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
        self.slug = self.get_slug()
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
        User, on_delete=models.CASCADE, verbose_name='Клиент'
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, verbose_name='Сервис подписки'
    )

    class Meta:
        abstract = True


class SubscriptionUserOrder(UserSubscription):
    """Модель связи заказа подписка-пользователь."""

    name = models.CharField(max_length=MAX_LENGTH, verbose_name='Имя клиента')
    phone_number = models.CharField(
        max_length=12, verbose_name='Номер телефона'
    )
    email = models.EmailField(verbose_name='Почтовый адрес')
    tariff = models.ForeignKey(
        Tariff,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Тариф',
    )
    due_date = models.DateTimeField(
        blank=True, null=True, verbose_name='Дата следующего списания'
    )
    pay_status = models.BooleanField(
        default=True, verbose_name='Статус оплаты'
    )
    task_id_celery = models.CharField(
        max_length=MAX_LENGTH,
        blank=True,
        null=True,
        verbose_name='Хранит id запланированной задачи селери',
    )

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

    def __str__(self) -> str:
        return f'{self.user} - {self.subscription}'

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


class Transaction(models.Model):

    TRANSACTION_TYPES = [
        ('DEBIT', 'Списание'),
        ('CASHBACK', 'Начисление кешбека'),
    ]
    STATUS_TYPES = [
        ('PENDING', 'Ожидается'),
        ('CREDITED', 'Зачислено'),
        ('PAID', 'Оплачено'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Клиент'
    )
    transaction_type = models.CharField(
        max_length=MAX_LENGTH,
        choices=TRANSACTION_TYPES,
        verbose_name='Тип транзакции',
    )
    transaction_date = models.DateTimeField(verbose_name='Дата транзакции')
    amount = models.IntegerField(verbose_name='Сумма транзакции')
    order = models.ForeignKey(
        SubscriptionUserOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Подписка на сервис',
    )
    status = models.CharField(
        max_length=MAX_LENGTH,
        choices=STATUS_TYPES,
        default='PENDING',
        verbose_name='Статус транзакции',
    )

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ('-transaction_date',)
