from django.urls import path

from .views import OdooHealthView

urlpatterns = [
    path("integrations/odoo/health/", OdooHealthView.as_view(), name="odoo-health"),
]
