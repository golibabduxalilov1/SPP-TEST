from django.apps import AppConfig


class OdooIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "integrations.odoo"
    label = "odoo_integration"
    verbose_name = "Odoo Integration"
