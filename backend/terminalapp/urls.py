from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConflictViewSet, SyncStatusView, TerminalBootstrapView, TerminalScanView,
    TerminalSyncView, TerminalWorkstationsView,
)

router = DefaultRouter()
router.register("conflicts", ConflictViewSet)

urlpatterns = [
    path("terminal/workstations", TerminalWorkstationsView.as_view(), name="terminal-workstations"),
    path("terminal/bootstrap", TerminalBootstrapView.as_view(), name="terminal-bootstrap"),
    path("terminal/scan", TerminalScanView.as_view(), name="terminal-scan"),
    path("terminal/sync", TerminalSyncView.as_view(), name="terminal-sync"),
    path("terminal/sync-status/<str:batch_id>", SyncStatusView.as_view(), name="terminal-sync-status"),
] + router.urls
