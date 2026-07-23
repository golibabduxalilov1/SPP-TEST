import re

from django.db.models import ProtectedError, RestrictedError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler

# DRF and simplejwt ship no "uz" locale, so their default messages render in
# English regardless of LANGUAGE_CODE. Translate the ones this API can actually
# emit; anything not listed here is left untouched rather than guessed at.
UZ_EXACT_MESSAGES = {
    "This field is required.": "Bu maydonni to'ldirish shart.",
    "This field may not be blank.": "Bu maydonni bo'sh qoldirib bo'lmaydi.",
    "This field may not be null.": "Bu maydon bo'sh bo'lishi mumkin emas.",
    "Not found.": "Topilmadi.",
    "Authentication credentials were not provided.": "Autentifikatsiya ma'lumotlari taqdim etilmagan.",
    "You do not have permission to perform this action.": "Bu amalni bajarish uchun ruxsatingiz yo'q.",
    "Incorrect authentication credentials.": "Autentifikatsiya ma'lumotlari noto'g'ri.",
    "User account is disabled.": "Foydalanuvchi akkaunti faol emas.",
    "A user with that username already exists.": "Bu foydalanuvchi nomi allaqachon band.",
    "Invalid token type": "Token turi noto'g'ri",
    "Token is invalid or expired": "Token yaroqsiz yoki muddati o'tgan",
    "Token is invalid or expired for type": "Token yaroqsiz yoki muddati o'tgan",
    "Given token not valid for any token type": "Berilgan token hech qanday token turi uchun yaroqli emas",
    "Authorization header must contain two space-delimited values": (
        "Authorization sarlavhasi ikkita bo'sh joy bilan ajratilgan qiymatdan iborat bo'lishi kerak"
    ),
}

# Parametrized DRF default messages — matched by regex, Uzbek template keeps the
# captured value(s) so field names / limits / pks still show correctly.
UZ_PATTERN_MESSAGES = [
    (re.compile(r'^Method "(.+)" not allowed\.$'), lambda m: f'"{m.group(1)}" metodiga ruxsat berilmagan.'),
    (
        re.compile(r'^Invalid pk "(.+)" - object does not exist\.$'),
        lambda m: f'"{m.group(1)}" identifikatorli obyekt mavjud emas.',
    ),
    (
        re.compile(r'^Ensure this field has no more than (\d+) characters\.$'),
        lambda m: f"Bu maydon {m.group(1)} ta belgidan oshmasligi kerak.",
    ),
    (
        re.compile(r'^Ensure this field has at least (\d+) characters\.$'),
        lambda m: f"Bu maydon kamida {m.group(1)} ta belgidan iborat bo'lishi kerak.",
    ),
    (
        re.compile(r'^Ensure this value is greater than or equal to (.+)\.$'),
        lambda m: f"Bu qiymat {m.group(1)} dan kichik bo'lmasligi kerak.",
    ),
    (
        re.compile(r'^Ensure this value is less than or equal to (.+)\.$'),
        lambda m: f"Bu qiymat {m.group(1)} dan katta bo'lmasligi kerak.",
    ),
]


def _translate_message(value):
    if not isinstance(value, str):
        return value
    if value in UZ_EXACT_MESSAGES:
        return UZ_EXACT_MESSAGES[value]
    for pattern, build in UZ_PATTERN_MESSAGES:
        match = pattern.match(value)
        if match:
            return build(match)
    return value


def _translate_response_data(data):
    if isinstance(data, dict):
        return {key: _translate_response_data(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_translate_response_data(item) for item in data]
    return _translate_message(data)


def api_exception_handler(exc, context):
    """Extends DRF's default handler so FK-protected deletes (on_delete=PROTECT)
    surface as a clean 400 instead of an unhandled 500 — this is the common
    case when deleting a parent row that still has dependent records. Also
    translates DRF/simplejwt's built-in English error messages to Uzbek, since
    neither package ships a "uz" locale for LANGUAGE_CODE to pick up."""
    if isinstance(exc, (ProtectedError, RestrictedError)):
        exc = ValidationError(
            {"detail": "Bu yozuvga bog'liq boshqa ma'lumotlar mavjud, shuning uchun o'chirib bo'lmaydi."}
        )
    response = exception_handler(exc, context)
    if response is not None:
        response.data = _translate_response_data(response.data)
    return response
