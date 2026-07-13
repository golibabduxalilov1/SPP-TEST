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


IsSuperAdmin = roles_allowed(Role.SUPER_ADMIN)
IsManagementRole = roles_allowed(Role.SUPER_ADMIN, Role.DIRECTOR, Role.MANAGER)
IsMasterOrAbove = roles_allowed(Role.SUPER_ADMIN, Role.DIRECTOR, Role.MANAGER, Role.MASTER)
IsTechnologistOrAbove = roles_allowed(Role.SUPER_ADMIN, Role.DIRECTOR, Role.MANAGER, Role.TECHNOLOGIST)
