from django.contrib import admin

from .models import AuditLog, LiveLogEvent, Notification, SystemSetting

admin.site.register(AuditLog)
admin.site.register(Notification)
admin.site.register(SystemSetting)
admin.site.register(LiveLogEvent)
