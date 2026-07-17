from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsSuperAdmin
from .models import ProductType, ProductTypeDetail
from .serializers import ProductTypeDetailSerializer, ProductTypeSerializer


class ProductTypeViewSet(viewsets.ModelViewSet):
    queryset = ProductType.objects.all().prefetch_related("details")
    serializer_class = ProductTypeSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "description"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        product_type = self.get_object()
        return Response(ProductTypeDetailSerializer(product_type.details.all(), many=True).data)


class ProductTypeDetailViewSet(viewsets.ModelViewSet):
    queryset = ProductTypeDetail.objects.select_related("product_type").all()
    serializer_class = ProductTypeDetailSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["product_type"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsSuperAdmin()]
        return [IsAuthenticated()]
