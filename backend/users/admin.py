from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'id',
        'last_name',
        'first_name',
    )
    ordering = ('last_name',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': (
            'first_name',
            'middle_name',
            'last_name'
        )}),
        (None, {'fields': ('balance',)})
    )

    add_fieldsets = (
        (None, {'fields': ('username', 'password1', 'password2')}),
        ('Personal info', {'fields': (
            'first_name',
            'middle_name',
            'last_name'
        )}),
    )
