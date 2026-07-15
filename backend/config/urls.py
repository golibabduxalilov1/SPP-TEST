from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("superadmin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("manufacturing.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("terminalapp.urls")),
    path("api/", include("packaging.urls")),
    path("api/", include("warehouse.urls")),
    path("api/", include("core.urls")),
    path("api/", include("integrations.odoo.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
