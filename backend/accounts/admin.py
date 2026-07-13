from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import TerminalSession, User


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("SPP", {"fields": ("role", "phone", "pin_code", "badge_token", "is_active_employee")}),
    )
    list_display = ("username", "first_name", "last_name", "role", "is_active_employee")
    list_filter = ("role", "is_active_employee")


admin.site.register(User, UserAdmin)
admin.site.register(TerminalSession)
