from django.contrib import admin

from .models import Device, Factory, Machine, Operation, Printer, Tsex, Workstation

admin.site.register(Factory)
admin.site.register(Tsex)
admin.site.register(Workstation)
admin.site.register(Machine)
admin.site.register(Operation)
admin.site.register(Device)
admin.site.register(Printer)
