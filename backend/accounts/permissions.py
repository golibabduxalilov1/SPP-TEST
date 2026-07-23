from rest_framework.permissions import BasePermission

from .models import Role


class RoleRequired(BasePermission):
    """Usage: permission_classes = [RoleRequired(['super_admin', 'director'])] via factory below."""

    allowed_roles: set = set()

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role in self.allowed_roles


def roles_allowed(*roles):
    class _Perm(RoleRequired):
        allowed_roles = set(roles)

    return _Perm


IsSuperAdmin = roles_allowed(Role.SUPER_ADMIN, Role.ADMIN)

# Management-level roles: view production/employee/report data and perform
# most non-employee-CRUD write actions (orders, production stage completion,
# conflict resolution). Replaces the former IsMasterOrAbove/IsTechnologistOrAbove/
# CanCompleteProductionStage classes, which collapsed to this exact set once
# Bosh usta/Texnolog were merged into Ishlab chiqarish menejeri.
IsManagementRole = roles_allowed(Role.SUPER_ADMIN, Role.ADMIN, Role.DIRECTOR, Role.MANAGER)

# Full employee account management (create, edit any field, delete, deactivate).
IsUserManagementRole = roles_allowed(Role.SUPER_ADMIN, Role.ADMIN)

# Department (Tsex) / machine / device / printer write access — Rahbar may
# view these but not manage them.
CanManageProduction = roles_allowed(Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER)

# QR-based order status updates: management roles plus the terminal roles that
# actually handle physical orders on the production/warehouse floor.
CanScanOrderStatus = roles_allowed(
    Role.SUPER_ADMIN, Role.ADMIN, Role.DIRECTOR, Role.MANAGER, Role.OPERATOR, Role.WAREHOUSE,
)
