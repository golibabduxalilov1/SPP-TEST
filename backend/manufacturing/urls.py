from rest_framework.routers import DefaultRouter

from .views import DeviceViewSet, MachineViewSet, OperationViewSet, PrinterViewSet, TsexViewSet, WorkstationViewSet

router = DefaultRouter()
router.register("tsexes", TsexViewSet)
router.register("workstations", WorkstationViewSet)
router.register("machines", MachineViewSet)
router.register("operations", OperationViewSet)
router.register("devices", DeviceViewSet)
router.register("printers", PrinterViewSet)

urlpatterns = router.urls
