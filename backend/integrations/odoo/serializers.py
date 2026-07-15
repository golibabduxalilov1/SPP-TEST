from rest_framework import serializers

from .models import SyncLog


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = ["id", "timestamp", "status", "orders_imported_count", "error_message"]
