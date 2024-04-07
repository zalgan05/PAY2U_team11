from django.contrib.auth.models import AbstractUser
from django.db import models

MAX_LENGTH = 64


class User(AbstractUser):
    """Модель пользователя"""

    first_name = models.CharField(max_length=MAX_LENGTH, verbose_name='Имя')
    middle_name = models.CharField(
        max_length=MAX_LENGTH, verbose_name='Отчество'
    )
    last_name = models.CharField(max_length=MAX_LENGTH, verbose_name='Фамилия')
    balance = models.IntegerField(
        null=True, blank=True, verbose_name='Денежный баланс'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.username}'
