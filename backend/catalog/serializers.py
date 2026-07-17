from rest_framework import serializers

from .models import ProductType, ProductTypeDetail


class ProductTypeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTypeDetail
        fields = ["id", "product_type", "name", "length_mm", "width_mm", "thickness_mm", "quantity", "material_type"]


class ProductTypeSerializer(serializers.ModelSerializer):
    details = ProductTypeDetailSerializer(many=True, read_only=True)

    class Meta:
        model = ProductType
        fields = ["id", "name", "description", "details", "created_at"]
