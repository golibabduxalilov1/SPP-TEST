from django.db.models import ProtectedError, RestrictedError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Extends DRF's default handler so FK-protected deletes (on_delete=PROTECT)
    surface as a clean 400 instead of an unhandled 500 — this is the common
    case when deleting a parent row that still has dependent records."""
    if isinstance(exc, (ProtectedError, RestrictedError)):
        exc = ValidationError(
            {"detail": "Bu yozuvga bog'liq boshqa ma'lumotlar mavjud, shuning uchun o'chirib bo'lmaydi."}
        )
    return exception_handler(exc, context)
