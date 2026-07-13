from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.audit import log_action
from .models import TerminalSession, User
from .permissions import IsManagementRole
from .serializers import AdminLoginSerializer, TerminalLoginSerializer, UserSerializer


class AdminLoginView(TokenObtainPairView):
    serializer_class = AdminLoginSerializer


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
            workstation_id=data.get("workstation_id"),
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
    search_fields = ["username", "first_name", "last_name", "phone"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, "employee.create", "User", instance.id, {"username": instance.username})

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, "employee.update", "User", instance.id, {"username": instance.username})
