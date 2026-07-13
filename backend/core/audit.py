def log_action(actor, action, entity_type="", entity_id="", details=None):
    from .models import AuditLog

    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else "",
        details=details or {},
    )


def push_live_log(event_type, message, meta=None):
    from .models import LiveLogEvent

    return LiveLogEvent.objects.create(event_type=event_type, message=message, meta=meta or {})
