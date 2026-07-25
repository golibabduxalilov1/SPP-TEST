from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import EmployeeStageMachine, Role, TerminalSession, User


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("SPP", {"fields": ("role", "department", "managed_departments", "phone", "pin_code_hash", "badge_token", "is_active_employee", "employment_status")}),
        # assigned_machines isn't listed here — it's a through-model M2M
        # (EmployeeStageMachine), which Django admin can't render inline;
        # see the EmployeeStageMachine registration below instead.
        ("Terminal bosqichi", {"fields": ("multi_stage_enabled", "assigned_operation", "assigned_operations")}),
        ("Xodim ma'lumotlari", {"fields": ("specialization", "uses_terminal")}),
    )
    list_display = ("username", "first_name", "last_name", "role", "department", "is_active_employee")
    list_filter = ("role", "is_active_employee")

    def get_readonly_fields(self, request, obj=None):
        # pin_code_hash is a hash, never a raw PIN — this admin form has no
        # hashing step, so it must stay read-only to avoid a plaintext value
        # being saved here by mistake. PIN changes go through the API (React
        # admin panel), which hashes them via UserSerializer.
        readonly = super().get_readonly_fields(request, obj) + ("pin_code_hash",)
        # A Super Admin's role is a one-way promotion — the model already enforces this
        # in save(), but locking the field too keeps the admin form from suggesting it's editable.
        if obj is not None and obj.role == Role.SUPER_ADMIN:
            readonly = (*readonly, "role")
        return readonly


class EmployeeStageMachineAdmin(admin.ModelAdmin):
    list_display = ("employee", "stage", "machine")
    list_filter = ("stage",)


admin.site.register(User, UserAdmin)
admin.site.register(TerminalSession)
admin.site.register(EmployeeStageMachine, EmployeeStageMachineAdmin)
