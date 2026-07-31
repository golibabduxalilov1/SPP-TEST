"""File reader / format detector for GibLab `.project` uploads.

Never trusts the `.project` extension alone: detects the real format from
file signatures/content, and never uses the uploaded filename as a
filesystem path. Guards against XXE, zip-slip, zip-bomb and plain
too-large-to-handle files.
"""

import zipfile
from io import BytesIO

from defusedxml import ElementTree as SafeET

from .constants import (
    MAX_PROJECT_FILE_SIZE, MAX_ZIP_COMPRESSION_RATIO, MAX_ZIP_MEMBER_COUNT, MAX_ZIP_UNCOMPRESSED_SIZE,
)
from .exceptions import GibLabImportError

ZIP_SIGNATURE = b"PK\x03\x04"


def read_uploaded_bytes(uploaded_file):
    """Read the whole upload once, enforcing the size ceiling first."""
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > MAX_PROJECT_FILE_SIZE:
        raise GibLabImportError("FILE_TOO_LARGE", f"Fayl hajmi {MAX_PROJECT_FILE_SIZE} baytdan katta")
    data = uploaded_file.read()
    if not data:
        raise GibLabImportError("INVALID_FILE", "Fayl bo'sh")
    if len(data) > MAX_PROJECT_FILE_SIZE:
        raise GibLabImportError("FILE_TOO_LARGE", f"Fayl hajmi {MAX_PROJECT_FILE_SIZE} baytdan katta")
    return data


def _looks_like_xml(data: bytes) -> bool:
    head = data.lstrip(b"\xef\xbb\xbf \t\r\n")[:200]
    return head.startswith(b"<")


def _extract_xml_from_zip(data: bytes) -> str:
    try:
        archive = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise GibLabImportError("INVALID_ARCHIVE", "Arxiv buzilgan yoki noto'g'ri formatda") from exc

    infos = archive.infolist()
    if len(infos) > MAX_ZIP_MEMBER_COUNT:
        raise GibLabImportError("INVALID_ARCHIVE", "Arxiv ichida juda ko'p fayl mavjud")

    total_uncompressed = 0
    xml_member = None
    for info in infos:
        # Zip-slip guard: reject any member whose name escapes the archive root.
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or ".." in name.split("/"):
            raise GibLabImportError("INVALID_ARCHIVE", "Arxiv xavfsiz bo'lmagan fayl nomiga ega")

        total_uncompressed += info.file_size
        if total_uncompressed > MAX_ZIP_UNCOMPRESSED_SIZE:
            raise GibLabImportError("INVALID_ARCHIVE", "Arxivni ochish natijasi juda katta (zip bomb ehtimoli)")
        if info.compress_size and info.file_size / max(info.compress_size, 1) > MAX_ZIP_COMPRESSION_RATIO:
            raise GibLabImportError("INVALID_ARCHIVE", "Arxiv siqilish darajasi shubhali (zip bomb ehtimoli)")

        if name.lower().endswith(".xml") or name.lower().endswith(".project"):
            if xml_member is None:
                xml_member = info

    if xml_member is None:
        raise GibLabImportError("INVALID_ARCHIVE", "Arxiv ichida XML fayl topilmadi")

    return archive.read(xml_member).decode("utf-8-sig", errors="strict")


def detect_and_extract(data: bytes) -> str:
    """Return the raw XML text, regardless of whether `data` was plain XML
    or a ZIP-wrapped `.project`. Raises GibLabImportError for anything else."""
    if data.startswith(ZIP_SIGNATURE):
        return _extract_xml_from_zip(data)

    if _looks_like_xml(data):
        try:
            return data.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise GibLabImportError("INVALID_XML", "Fayl encoding noto'g'ri (UTF-8 kutilgan)") from exc

    raise GibLabImportError("UNSUPPORTED_PROJECT_FORMAT", "Fayl formati aniqlanmadi (XML yoki ZIP kutilgan)")


def parse_xml_safely(xml_text: str):
    """Parse with defusedxml (blocks XXE / external entity / DTD expansion)
    and confirm a root element exists."""
    try:
        root = SafeET.fromstring(xml_text)
    except Exception as exc:  # noqa: BLE001 - any parser failure is INVALID_XML to the caller
        raise GibLabImportError("INVALID_XML", f"XML tahlil qilib bo'lmadi: {exc}") from exc
    if root is None:
        raise GibLabImportError("INVALID_XML", "Root element topilmadi")
    return root
