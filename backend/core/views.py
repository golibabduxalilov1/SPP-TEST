from datetime import date

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from manufacturing.models import Machine

from . import dashboard_metrics
from . import reports as reports_service
from . import reports_export, reports_orders
from .audit import log_action
from .dashboard import build_summary
from .models import AuditLog, LiveLogEvent
from .serializers import AuditLogSerializer, LiveLogEventSerializer
from .tablo import build_production_table


def _parse_report_date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def _orders_report_filters(request):
    today = timezone.localdate()
    date_from = _parse_report_date(request.query_params.get("from"), today)
    date_to = _parse_report_date(request.query_params.get("to"), today)
    status = request.query_params.get("status") or None
    worker_id = request.query_params.get("worker") or None
    department_id = request.query_params.get("department") or None
    granularity = request.query_params.get("granularity", "day")
    return date_from, date_to, status, worker_id, department_id, granularity


class ProductionTableView(APIView):
    def get(self, request):
        mode = request.query_params.get("mode", "hajm")
        return Response(build_production_table(mode))


class DashboardSummaryView(APIView):
    def get(self, request):
        return Response(build_summary())


class DashboardLiveLogsView(APIView):
    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
        events = LiveLogEvent.objects.all()[:limit]
        return Response(LiveLogEventSerializer(events, many=True).data)


class DashboardOverviewView(APIView):
    def get(self, request):
        date_from, date_to, _ = dashboard_metrics.parse_window(request)
        return Response(dashboard_metrics.overview(date_from, date_to))


class DashboardMachinesView(APIView):
    def get(self, request):
        date_from, date_to, _ = dashboard_metrics.parse_window(request)
        return Response(dashboard_metrics.machines_summary(date_from, date_to))


class DashboardMachineSeriesView(APIView):
    def get(self, request, machine_id):
        machine = get_object_or_404(Machine.objects.select_related("operation"), pk=machine_id)
        date_from, date_to, interval_minutes = dashboard_metrics.parse_window(request)
        return Response(dashboard_metrics.machine_series(machine, date_from, date_to, interval_minutes))


class DashboardLeaderboardView(APIView):
    def get(self, request):
        date_from, date_to, _ = dashboard_metrics.parse_window(request)
        limit = int(request.query_params.get("limit", 10))
        return Response(dashboard_metrics.leaderboard(date_from, date_to, limit))


class ReportProductionView(APIView):
    def get(self, request):
        return Response(reports_service.production_report())


class ReportOrdersView(APIView):
    def get(self, request):
        return Response(reports_service.orders_report())


class ReportMachinesView(APIView):
    def get(self, request):
        return Response(reports_service.machines_report())


class ReportScansView(APIView):
    def get(self, request):
        return Response(reports_service.scans_report())


class ReportWarehouseView(APIView):
    def get(self, request):
        return Response(reports_service.warehouse_report())


class OrdersReportOverviewView(APIView):
    def get(self, request):
        date_from, date_to, status, worker_id, department_id, granularity = _orders_report_filters(request)
        return Response(reports_orders.overview(date_from, date_to, status, worker_id, department_id, granularity))


class OrdersReportWorkerCompletedView(APIView):
    def get(self, request, worker_id):
        date_from, date_to, *_rest = _orders_report_filters(request)
        return Response(reports_orders.worker_completed_orders(worker_id, date_from, date_to))


class OrdersReportExportView(APIView):
    def get(self, request):
        date_from, date_to, status, worker_id, department_id, granularity = _orders_report_filters(request)
        data = reports_orders.overview(date_from, date_to, status, worker_id, department_id, granularity)
        fmt = (request.query_params.get("file_type") or "pdf").lower()
        if fmt in ("excel", "xlsx"):
            buf = reports_export.render_orders_report_excel(data)
            response = FileResponse(
                buf, as_attachment=True, filename="hisobot.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            buf = reports_export.render_orders_report_pdf(data)
            response = FileResponse(buf, as_attachment=True, filename="hisobot.pdf", content_type="application/pdf")
        log_action(request.user, "reports.export", details={"format": fmt})
        return response


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["action", "entity_type"]
