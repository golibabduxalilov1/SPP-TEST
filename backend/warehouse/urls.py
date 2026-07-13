from django.urls import path

from .views import WarehouseDeliverView, WarehousePackagesView, WarehouseReceiveView

urlpatterns = [
    path("warehouse/packages", WarehousePackagesView.as_view(), name="warehouse-packages"),
    path("warehouse/receive", WarehouseReceiveView.as_view(), name="warehouse-receive"),
    path("warehouse/deliver", WarehouseDeliverView.as_view(), name="warehouse-deliver"),
]
