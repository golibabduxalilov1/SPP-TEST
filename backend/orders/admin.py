from django.contrib import admin

from .models import Label, Order, Part, PartRoute, Product

admin.site.register(Order)
admin.site.register(Product)
admin.site.register(Part)
admin.site.register(PartRoute)
admin.site.register(Label)
