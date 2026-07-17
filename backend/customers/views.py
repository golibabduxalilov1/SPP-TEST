from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsTechnologistOrAbove
from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "phone", "address"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsTechnologistOrAbove()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"])
    def lookup(self, request):
        """Find a customer by exact phone match — used to autofill the order form."""
        phone = (request.query_params.get("phone") or "").strip()
        if not phone:
            return Response(None)
        customer = Customer.objects.filter(phone=phone).first()
        return Response(CustomerSerializer(customer).data if customer else None)
