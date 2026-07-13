from django.contrib import admin

from .models import Package, PackageItem

admin.site.register(Package)
admin.site.register(PackageItem)
