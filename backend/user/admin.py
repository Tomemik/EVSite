from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "team")
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('team',)}),
    )


admin.site.register(User, CustomUserAdmin)
