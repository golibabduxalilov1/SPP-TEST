from rest_framework import serializers

from .models import AuditLog, LiveLogEvent


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = "__all__"

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() or obj.actor.username if obj.actor else "system"


class LiveLogEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveLogEvent
        fields = "__all__"
