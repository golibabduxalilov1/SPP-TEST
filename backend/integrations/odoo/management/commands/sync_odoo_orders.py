import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from integrations.odoo.services import sync_orders_from_odoo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Poll Odoo Cloud (read-only) for confirmed sale.order records and mirror them "
        "into SPP as Orders. One-way sync — never writes back to Odoo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--once", action="store_true",
            help="Run a single sync pass and exit, instead of looping forever.",
        )

    def handle(self, *args, **options):
        if options["once"]:
            result = sync_orders_from_odoo()
            self.stdout.write(self.style.SUCCESS(f"Odoo sync (once): {result}"))
            return

        if not settings.ODOO_SYNC_ENABLED:
            self.stdout.write(self.style.WARNING("ODOO_SYNC_ENABLED=False — sync tsikli ishga tushmadi."))
            return

        interval = settings.ODOO_SYNC_INTERVAL_SECONDS
        self.stdout.write(self.style.SUCCESS(f"Odoo sync tsikli boshlandi (har {interval} soniyada)."))
        while True:
            try:
                result = sync_orders_from_odoo()
                logger.info("Odoo sync completed: %s", result)
            except Exception:
                logger.exception("Odoo sync tsiklida kutilmagan xatolik — keyingi urinishga o'tildi")
            time.sleep(interval)
