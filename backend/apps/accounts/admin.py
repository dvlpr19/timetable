from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "last_name", "first_name", "role", "language", "is_active")
    list_filter = ("role", "language", "is_active")
    fieldsets = (
        *BaseUserAdmin.fieldsets,
        (
            _("Timetable"),
            {"fields": ("role", "language", "language_auto", "faculty", "department")},
        ),
    )
