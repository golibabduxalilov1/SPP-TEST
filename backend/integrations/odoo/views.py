from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSuperAdmin

from .client import OdooClient
from .models import SyncLog
from .serializers import SyncLogSerializer


class OdooHealthView(APIView):
    """Read-only status view: reports sync state and pings Odoo via authenticate only."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        last_log = SyncLog.objects.first()
        last_success = SyncLog.objects.filter(status=SyncLog.Status.SUCCESS).first()

        connection_ok = OdooClient().test_connection() if settings.ODOO_SYNC_ENABLED else False

        next_sync_in_seconds = None
        if last_log:
            elapsed = (timezone.now() - last_log.timestamp).total_seconds()
            next_sync_in_seconds = max(0, int(settings.ODOO_SYNC_INTERVAL_SECONDS - elapsed))

        return Response({
            "sync_enabled": settings.ODOO_SYNC_ENABLED,
            "interval_seconds": settings.ODOO_SYNC_INTERVAL_SECONDS,
            "connection_ok": connection_ok,
            "last_sync_at": last_log.timestamp if last_log else None,
            "last_success_at": last_success.timestamp if last_success else None,
            "next_sync_in_seconds": next_sync_in_seconds,
            "recent_logs": SyncLogSerializer(SyncLog.objects.all()[:10], many=True).data,
        })
