from rest_framework.routers import DefaultRouter

from .views import ProductTypeDetailViewSet, ProductTypeViewSet

router = DefaultRouter()
router.register("product-types", ProductTypeViewSet)
router.register("product-type-details", ProductTypeDetailViewSet)

urlpatterns = router.urls
