"""Read-only XML-RPC client for Odoo Cloud (SaaS) sale.order data.

Only ``common.authenticate`` and ``search_read`` are ever called against
Odoo. No ``create``, ``write`` or ``unlink`` method is implemented here —
this integration is strictly one-way (Odoo -> SPP) and this client is the
only place that talks to Odoo, so that guarantee holds for the whole app.
"""

import logging
import xmlrpc.client

from django.conf import settings

logger = logging.getLogger(__name__)

SALE_ORDER_FIELDS = ["id", "name", "partner_id", "date_order", "commitment_date", "amount_total", "state"]


class OdooAuthenticationError(Exception):
    pass


class OdooClient:
    def __init__(self, url=None, db=None, username=None, api_key=None):
        self.url = (url or settings.ODOO_URL).rstrip("/")
        self.db = db or settings.ODOO_DB
        self.username = username or settings.ODOO_USERNAME
        self.api_key = api_key or settings.ODOO_API_KEY
        self._uid = None

    def _authenticate(self):
        if self._uid is not None:
            return self._uid
        if not (self.url and self.db and self.username and self.api_key):
            raise OdooAuthenticationError("Odoo ulanish sozlamalari to'liq emas (.env faylini tekshiring)")
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        uid = common.authenticate(self.db, self.username, self.api_key, {})
        if not uid:
            raise OdooAuthenticationError("Odoo autentifikatsiyasi muvaffaqiyatsiz — login yoki API key noto'g'ri")
        self._uid = uid
        return uid

    def _object_proxy(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def test_connection(self):
        """Read-only connectivity check for the health endpoint (authenticate only)."""
        try:
            self._authenticate()
            return True
        except Exception as exc:
            logger.error("Odoo health check failed: %s", exc)
            return False

    def fetch_confirmed_orders(self, since_datetime=None):
        """Return confirmed (state='sale') sale.order records via search_read.

        Connection/authentication/RPC failures are logged here and re-raised
        so the caller (sync_orders_from_odoo) can record an accurate failed
        SyncLog entry — swallowing them here would make a broken connection
        silently look like "0 new orders" instead of a failure.
        """
        try:
            uid = self._authenticate()
        except OdooAuthenticationError as exc:
            logger.error("Odoo authentication error: %s", exc)
            raise

        domain = [["state", "=", "sale"]]
        if since_datetime:
            domain.append(["date_order", ">=", since_datetime.strftime("%Y-%m-%d %H:%M:%S")])

        try:
            return self._object_proxy().execute_kw(
                self.db, uid, self.api_key,
                "sale.order", "search_read",
                [domain],
                {"fields": SALE_ORDER_FIELDS},
            )
        except Exception as exc:
            logger.error("Odoo fetch_confirmed_orders failed: %s", exc)
            raise
