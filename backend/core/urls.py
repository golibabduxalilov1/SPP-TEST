from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditLogViewSet, DashboardLeaderboardView, DashboardLiveLogsView, DashboardMachinesView,
    DashboardMachineSeriesView, DashboardOverviewView, DashboardSummaryView, OrdersReportExportView,
    OrdersReportOverviewView, OrdersReportWorkerCompletedView, ProductionTableView,
    ReportMachinesView, ReportOrdersView, ReportProductionView, ReportScansView, ReportWarehouseView,
)

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet)

urlpatterns = [
    path("production/table", ProductionTableView.as_view(), name="production-table"),
    path("dashboard/summary", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/live-logs", DashboardLiveLogsView.as_view(), name="dashboard-live-logs"),
    path("dashboard/overview", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("dashboard/machines", DashboardMachinesView.as_view(), name="dashboard-machines"),
    path("dashboard/machines/<int:machine_id>/series", DashboardMachineSeriesView.as_view(), name="dashboard-machine-series"),
    path("dashboard/leaderboard", DashboardLeaderboardView.as_view(), name="dashboard-leaderboard"),
    path("reports/production", ReportProductionView.as_view(), name="reports-production"),
    path("reports/orders", ReportOrdersView.as_view(), name="reports-orders"),
    path("reports/machines", ReportMachinesView.as_view(), name="reports-machines"),
    path("reports/scans", ReportScansView.as_view(), name="reports-scans"),
    path("reports/warehouse", ReportWarehouseView.as_view(), name="reports-warehouse"),
    path("reports/orders/overview", OrdersReportOverviewView.as_view(), name="reports-orders-overview"),
    path("reports/orders/workers/<int:worker_id>/completed", OrdersReportWorkerCompletedView.as_view(), name="reports-orders-worker-completed"),
    path("reports/orders/export", OrdersReportExportView.as_view(), name="reports-orders-export"),
] + router.urls
