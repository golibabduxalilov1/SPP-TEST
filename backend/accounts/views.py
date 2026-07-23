from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.audit import log_action
from .models import Role, TerminalSession, User
from .permissions import IsManagementRole
from .serializers import (
    AdminLoginSerializer, TerminalLoginSerializer, TerminalPinLookupSerializer, UserSerializer,
)

_USER_MANAGEMENT_ROLES = {Role.SUPER_ADMIN, Role.ADMIN}
_WORKPLACE_ONLY_FIELDS = {"department", "assigned_machines"}


class AdminLoginView(TokenObtainPairView):
    serializer_class = AdminLoginSerializer


def _operation_payload(operation, employee):
    machines = employee.assigned_machines.filter(operation=operation)
    return {
        "id": operation.id,
        "code": operation.code,
        "name": operation.name,
        "machines": [{"id": m.id, "machine_id": m.machine_id, "name": m.name} for m in machines],
    }


class TerminalPinLookupView(APIView):
    """Identifies an employee by PIN alone, before any session/token exists —
    used by the terminal's quick-login screen to auto-resolve their assigned
    stage(s) (or fall back to manual stage selection if none are assigned)."""

    permission_classes = []

    def post(self, request):
        serializer = TerminalPinLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pin_code = serializer.validated_data["pin_code"]

        user = User.objects.filter(pin_code=pin_code, is_active_employee=True).first()
        if not user or not user.can_use_terminal:
            return Response({"detail": "PIN kod noto'g'ri"}, status=status.HTTP_401_UNAUTHORIZED)

        if user.multi_stage_enabled:
            operations = list(user.assigned_operations.all())
        elif user.assigned_operation:
            operations = [user.assigned_operation]
        else:
            operations = []

        return Response(
            {
                "employee": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role_display": user.get_role_display(),
                },
                "operations": [_operation_payload(op, user) for op in operations],
            }
        )


class TerminalLoginView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = TerminalLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = None
        if data.get("pin_code"):
            user = User.objects.filter(pin_code=data["pin_code"], is_active_employee=True).first()
        elif data.get("badge_token"):
            user = User.objects.filter(badge_token=data["badge_token"], is_active_employee=True).first()

        if not user or not user.can_use_terminal:
            return Response({"detail": "PIN yoki badge noto'g'ri"}, status=status.HTTP_401_UNAUTHORIZED)

        # A single employee may only hold one active terminal session at a time.
        TerminalSession.objects.filter(employee=user, is_active=True).update(
            is_active=False, ended_at=timezone.now()
        )
        session = TerminalSession.objects.create(
            employee=user,
            operation_id=data.get("operation_id"),
            device_id=data["device_id"],
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "session_id": str(session.id),
                "employee": UserSerializer(user).data,
            }
        )


class TerminalLogoutView(APIView):
    def post(self, request):
        session_id = request.data.get("session_id")
        qs = TerminalSession.objects.filter(employee=request.user, is_active=True)
        if session_id:
            qs = qs.filter(id=session_id)
        qs.update(is_active=False, ended_at=timezone.now())
        return Response({"detail": "Sessiya tugatildi"})


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsManagementRole]
    filterset_fields = ["role", "is_active_employee"]
    search_fields = ["phone", "first_name", "last_name"]

    def perform_create(self, serializer):
        if self.request.user.role not in _USER_MANAGEMENT_ROLES:
            raise PermissionDenied("Xodim qo'shish huquqi faqat Super Admin va Admin'da.")
        # Admin has the same privilege level as Super Admin, except it may not
        # create a Super Admin account.
        if serializer.validated_data.get("role") == Role.SUPER_ADMIN and self.request.user.role == Role.ADMIN:
            raise PermissionDenied("Admin super admin qo'sha olmaydi.")
        instance = serializer.save()
        log_action(self.request.user, "employee.create", "User", instance.id, {"phone": instance.phone})

    def perform_update(self, serializer):
        is_self = serializer.instance == self.request.user
        requester_role = self.request.user.role
        if is_self:
            # Only a Super Admin may edit their own account via this endpoint —
            # and even then, never their own phone number (it's the login field).
            if requester_role != Role.SUPER_ADMIN:
                raise PermissionDenied("O'zingizni tahrirlay olmaysiz.")
            new_phone = serializer.validated_data.get("phone")
            if new_phone is not None and new_phone != self.request.user.phone:
                raise PermissionDenied("O'zingizning telefon raqamingizni o'zgartira olmaysiz.")
            new_role = serializer.validated_data.get("role")
            if new_role is not None and new_role != Role.SUPER_ADMIN:
                raise PermissionDenied("Super admin o'z rolini o'zgartira olmaydi.")
        else:
            # Super admins are fully protected from being managed via this endpoint by
            # anyone else — no one (including another super admin) may update,
            # deactivate, or otherwise change any field on another super admin account here.
            if serializer.instance.role == Role.SUPER_ADMIN:
                raise PermissionDenied("Super adminni tahrirlab bo'lmaydi.")
            if requester_role == Role.DIRECTOR:
                raise PermissionDenied("Sizda xodimlarni tahrirlash huquqi yo'q, faqat ko'rish mumkin.")
            if requester_role == Role.MANAGER:
                if not set(serializer.validated_data.keys()) <= _WORKPLACE_ONLY_FIELDS:
                    raise PermissionDenied("Sizda faqat xodimni bo'lim va stanokka biriktirish huquqi bor.")
            elif requester_role not in _USER_MANAGEMENT_ROLES:
                raise PermissionDenied("Xodimni tahrirlash huquqingiz yo'q.")
            if serializer.validated_data.get("role") == Role.SUPER_ADMIN and requester_role == Role.ADMIN:
                raise PermissionDenied("Admin super admin tayinlay olmaydi.")
        instance = serializer.save()
        log_action(self.request.user, "employee.update", "User", instance.id, {"phone": instance.phone})

    def perform_destroy(self, instance):
        if self.request.user.role not in _USER_MANAGEMENT_ROLES:
            raise PermissionDenied("Xodimni o'chirish huquqi faqat Super Admin va Admin'da.")
        if instance == self.request.user:
            raise PermissionDenied("O'zingizni o'chira olmaysiz.")
        # Super admins are the only role allowed to manage other super admins, but
        # they must not be able to delete each other via this endpoint.
        if instance.role == Role.SUPER_ADMIN:
            raise PermissionDenied("Super adminni o'chirib bo'lmaydi.")
        instance.delete()
        log_action(self.request.user, "employee.delete", "User", instance.id, {"phone": instance.phone})
