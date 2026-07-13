from django.contrib import admin

from .models import Conflict, OfflineSyncBatch, ScanEvent

admin.site.register(ScanEvent)
admin.site.register(OfflineSyncBatch)
admin.site.register(Conflict)
