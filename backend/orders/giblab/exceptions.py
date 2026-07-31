"""Structured import errors for the GibLab pipeline.

Every raised/collected error carries enough structure for the API layer to
return `{"code", "message", "entity_type", "external_id", "xml_path",
"details"}` without ever leaking a stack trace or raw SQL to the client.
"""


class GibLabImportError(Exception):
    def __init__(self, code, message, entity_type="", external_id="", xml_path="", details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.entity_type = entity_type
        self.external_id = str(external_id) if external_id else ""
        self.xml_path = xml_path
        self.details = details or {}

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "entity_type": self.entity_type,
            "external_id": self.external_id,
            "xml_path": self.xml_path,
            "details": self.details,
        }


class GibLabValidationFailed(Exception):
    """Raised by `service.import_project_file` when the import plan has
    blocking errors -- nothing was written to the database."""

    def __init__(self, errors, warnings=None):
        super().__init__("GibLab import validation failed")
        self.errors = errors
        self.warnings = warnings or []


def error_dict(code, message, entity_type="", external_id="", xml_path="", details=None):
    """Build the same structured shape as `GibLabImportError.to_dict()`
    without raising -- used by the validator/mapper to collect multiple
    errors/warnings instead of failing on the first one."""
    return GibLabImportError(code, message, entity_type, external_id, xml_path, details).to_dict()
