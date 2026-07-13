from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PackageLabelPrintView, PackageViewSet, PackagingCompleteView, PackagingScanView, PackagingStartView

router = DefaultRouter()
router.register("packages", PackageViewSet)

urlpatterns = [
    path("packaging/start", PackagingStartView.as_view(), name="packaging-start"),
    path("packaging/scan", PackagingScanView.as_view(), name="packaging-scan"),
    path("packaging/complete", PackagingCompleteView.as_view(), name="packaging-complete"),
    path("packaging/label-print", PackageLabelPrintView.as_view(), name="packaging-label-print"),
] + router.urls
