from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Role, TerminalSession, User


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("SPP", {"fields": ("role", "department", "phone", "pin_code", "badge_token", "is_active_employee")}),
        ("Terminal bosqichi", {"fields": ("multi_stage_enabled", "assigned_operation", "assigned_operations", "assigned_machines")}),
    )
    list_display = ("username", "first_name", "last_name", "role", "department", "is_active_employee")
    list_filter = ("role", "is_active_employee")

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        # A Super Admin's role is a one-way promotion — the model already enforces this
        # in save(), but locking the field too keeps the admin form from suggesting it's editable.
        if obj is not None and obj.role == Role.SUPER_ADMIN:
            readonly = (*readonly, "role")
        return readonly


admin.site.register(User, UserAdmin)
admin.site.register(TerminalSession)
