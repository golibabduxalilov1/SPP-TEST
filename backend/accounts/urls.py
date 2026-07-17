from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminLoginView, MeView, TerminalLoginView, TerminalLogoutView, TerminalPinLookupView, UserViewSet,
)

router = DefaultRouter()
router.register("employees", UserViewSet)

urlpatterns = [
    path("auth/login", AdminLoginView.as_view(), name="admin-login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/terminal-pin-lookup", TerminalPinLookupView.as_view(), name="terminal-pin-lookup"),
    path("auth/terminal-login", TerminalLoginView.as_view(), name="terminal-login"),
    path("auth/logout", TerminalLogoutView.as_view(), name="terminal-logout"),
    path("me", MeView.as_view(), name="me"),
] + router.urls
