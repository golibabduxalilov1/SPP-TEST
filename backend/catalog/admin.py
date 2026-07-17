from django.contrib import admin

from .models import ProductType, ProductTypeDetail


class ProductTypeDetailInline(admin.TabularInline):
    model = ProductTypeDetail
    extra = 0


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]
    inlines = [ProductTypeDetailInline]
