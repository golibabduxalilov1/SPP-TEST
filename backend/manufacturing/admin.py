from django.contrib import admin

from .models import Device, Machine, Operation, Printer, Tsex

admin.site.register(Tsex)
admin.site.register(Machine)
admin.site.register(Operation)
admin.site.register(Device)
admin.site.register(Printer)
