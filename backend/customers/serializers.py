from rest_framework import serializers

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    orders_count = serializers.IntegerField(source="orders.count", read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "address", "created_at", "orders_count"]
