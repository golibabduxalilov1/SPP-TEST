from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User
from catalog.models import ProductType, ProductTypeDetail
from manufacturing.models import Machine, Operation, Tsex, Workstation
from orders.constants import OPERATION_SEEDS
from orders.models import Order, Product
from orders.services import assign_route


PRODUCT_TYPE_SEEDS = [
    {
        "name": "Shkaf Istanbul 1800",
        "description": "Uch eshikli zamonaviy kiyim shkafi",
        "details": [
            ("Yon devor", 1800, 550, 18, 2, "LDSP"),
            ("Tokcha", 864, 500, 18, 4, "LDSP"),
            ("Fasad", 1796, 596, 18, 3, "MDF"),
        ],
    },
    {
        "name": "Oshxona shkafi Modern",
        "description": "Oshxona uchun osma modul shkaf",
        "details": [
            ("Yon panel", 720, 300, 18, 2, "LDSP"),
            ("Yuqori va pastki panel", 764, 300, 18, 2, "LDSP"),
            ("Fasad", 716, 396, 18, 2, "MDF"),
        ],
    },
    {
        "name": "Komod Classic",
        "description": "To'rt tortmali klassik komod",
        "details": [
            ("Yon devor", 850, 450, 18, 2, "LDSP"),
            ("Tortma fasadi", 196, 796, 18, 4, "MDF"),
            ("Ustki panel", 836, 470, 18, 1, "LDSP"),
        ],
    },
    {
        "name": "Yozuv stoli Loft",
        "description": "Ish va o'qish uchun loft uslubidagi stol",
        "details": [
            ("Stol usti", 1200, 600, 25, 1, "LDSP"),
            ("Yon tayanch", 720, 550, 18, 2, "LDSP"),
            ("Old bog'lama", 1100, 250, 18, 1, "LDSP"),
        ],
    },
    {
        "name": "Kompyuter stoli Corner",
        "description": "Burchak uchun ixcham kompyuter stoli",
        "details": [
            ("Burchak stol usti", 1400, 900, 25, 1, "LDSP"),
            ("Yon tayanch", 720, 500, 18, 2, "LDSP"),
            ("Klaviatura tokchasi", 600, 300, 18, 1, "LDSP"),
        ],
    },
    {
        "name": "Kitob javoni Oxford",
        "description": "Besh qavatli ochiq kitob javoni",
        "details": [
            ("Yon devor", 1900, 300, 18, 2, "LDSP"),
            ("Tokcha", 764, 280, 18, 5, "LDSP"),
            ("Orqa devor", 1900, 800, 4, 1, "DVP"),
        ],
    },
    {
        "name": "TV tumba Minimal",
        "description": "Minimal uslubdagi past TV tumbasi",
        "details": [
            ("Ustki panel", 1600, 420, 18, 1, "LDSP"),
            ("Yon devor", 400, 400, 18, 2, "LDSP"),
            ("Fasad", 396, 796, 18, 2, "MDF"),
        ],
    },
    {
        "name": "Krovat Comfort 1600",
        "description": "Ikki kishilik yumshoq boshli krovat",
        "details": [
            ("Bosh panel", 1800, 1000, 25, 1, "MDF"),
            ("Yon bog'lama", 2000, 300, 25, 2, "LDSP"),
            ("Oyoq panel", 1800, 400, 25, 1, "MDF"),
        ],
    },
    {
        "name": "Tungi tumba Nova",
        "description": "Yotoqxona uchun ikki tortmali tumba",
        "details": [
            ("Yon devor", 500, 400, 18, 2, "LDSP"),
            ("Tortma fasadi", 196, 446, 18, 2, "MDF"),
            ("Ustki panel", 500, 420, 18, 1, "LDSP"),
        ],
    },
    {
        "name": "Kiyim ilgich Hall",
        "description": "Dahliz uchun devoriy kiyim ilgich",
        "details": [
            ("Asosiy panel", 1200, 600, 18, 1, "LDSP"),
            ("Yuqori tokcha", 600, 300, 18, 1, "LDSP"),
            ("Pastki tumba fasadi", 396, 596, 18, 2, "MDF"),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed SPP demo data: tsex, workstations, machines, operations, users, sample order."

    @transaction.atomic
    def handle(self, *args, **options):
        for seed in OPERATION_SEEDS:
            # Do not overwrite names/order changed by Super Admin when demo data is re-seeded.
            Operation.objects.get_or_create(code=seed["code"], defaults=seed)
        self.stdout.write(self.style.SUCCESS(f"Operations: {Operation.objects.count()}"))

        tsex, _ = Tsex.objects.get_or_create(name="Asosiy Tsex")

        workstations = {}
        for op in Operation.objects.all():
            ws, _ = Workstation.objects.get_or_create(
                tsex=tsex, operation=op, name=f"{op.name} post", defaults={"status": "active"}
            )
            workstations[op.code] = ws
            Machine.objects.get_or_create(
                machine_id=f"M-{op.code}", operation=op, workstation=ws,
                defaults={"name": f"01 {op.name}", "status": "active"},
            )

        users = [
            ("admin", "+998901234501", Role.SUPER_ADMIN, "Admin", "Adminov", None),
            ("direktor", "+998901234502", Role.DIRECTOR, "Bekzod", "Rahbarov", None),
            ("menejer", "+998901234503", Role.MANAGER, "Sardor", "Menejerov", None),
            ("master1", "+998901234504", Role.MASTER, "Sherzod", "Masterov", "1001"),
            ("texnolog1", "+998901234505", Role.TECHNOLOGIST, "Nodir", "Texnologov", None),
            ("usta1", "+998901234506", Role.OPERATOR, "Alisher", "Ustaev", "1002"),
            ("qadoqchi1", "+998901234507", Role.PACKAGING, "Jasur", "Qadoqchiev", "1003"),
            ("omborchi1", "+998901234508", Role.WAREHOUSE, "Bahrom", "Omborchiev", "1004"),
        ]
        default_password = "spp12345"
        for username, phone, role, first, last, pin in users:
            user = User.objects.filter(phone=phone).first() or User.objects.filter(username=username).first()
            created = user is None
            if created:
                user = User(username=username, phone=phone, first_name=first, last_name=last)
            if created:
                user.set_password(default_password)
                user.role = role
                user.is_staff = role == Role.SUPER_ADMIN
                user.is_superuser = role == Role.SUPER_ADMIN
                user.pin_code = pin or ""
                user.save()
        self.stdout.write(self.style.SUCCESS(f"Users: {User.objects.count()} (default password: {default_password})"))

        for product_seed in PRODUCT_TYPE_SEEDS:
            product_type, _ = ProductType.objects.get_or_create(
                name=product_seed["name"],
                defaults={"description": product_seed["description"]},
            )
            for name, length, width, thickness, qty, material in product_seed["details"]:
                ProductTypeDetail.objects.get_or_create(
                    product_type=product_type,
                    name=name,
                    defaults={
                        "length_mm": length,
                        "width_mm": width,
                        "thickness_mm": thickness,
                        "quantity": qty,
                        "material_type": material,
                    },
                )
        self.stdout.write(self.style.SUCCESS(f"Product types: {ProductType.objects.count()}"))

        if not Order.objects.exists():
            order = Order.objects.create(
                customer_name="Shkaf Istanbul mijozi",
                customer_phone="+998901234567",
                product_name="Shkaf Istanbul 1800",
                deadline=None,
                priority=Order.Priority.NORMAL,
                status=Order.Status.IN_PRODUCTION,
            )
            product = Product.objects.create(order=order, name="Shkaf Istanbul 1800")
            demo_parts = [
                ("KN70001_01_001", "Yon bok", "LDSP", "Sonoma", 480, 706, 18, 2, "oddiy_panel"),
                ("KN70001_01_002", "Lev bok", "LDSP", "Sonoma", 480, 706, 18, 1, "oddiy_panel"),
                ("KN70001_01_003", "Polka", "LDSP", "Sonoma", 400, 300, 16, 3, "faqat_kesish"),
                ("KN70001_01_004", "Fasad", "MDF", "Oq", 396, 596, 18, 2, "cnc"),
                ("KN70001_01_005", "Karkas tayanchi", "Massiv", "Yong'oq", 40, 40, 400, 4, "stolyarka"),
            ]
            from orders.models import Part

            for code, name, material, color, length, width, thickness, qty, route_key in demo_parts:
                part = Part.objects.create(
                    order=order, product=product, code=code, name=name, material=material, color=color,
                    length_mm=length, width_mm=width, thickness_mm=thickness, quantity=qty,
                    area_m2=round((length * width) / 1_000_000 * qty, 3), edge_meter=round((length + width) * 2 / 1000 * qty, 2),
                    drilling_count=4,
                )
                assign_route(part, route_key)
            self.stdout.write(self.style.SUCCESS(f"Demo order created: #{order.order_no}"))

        self.stdout.write(self.style.SUCCESS("Seed complete."))
