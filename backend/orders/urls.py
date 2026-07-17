from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LabelPreviewView, LabelPrintView, OrderDetailItemViewSet, OrderViewSet, PartViewSet

router = DefaultRouter()
router.register("orders", OrderViewSet)
router.register("parts", PartViewSet)
router.register("order-details", OrderDetailItemViewSet)

urlpatterns = [
    path("labels/preview", LabelPreviewView.as_view(), name="labels-preview"),
    path("labels/print", LabelPrintView.as_view(), name="labels-print"),
] + router.urls
