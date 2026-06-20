# ═══════════════════════════════════════════════════════════════════════
# EDM v2.1 — Seed Script (development data)
# Creates: 1 demo company, 1 admin user, 1 Poimenidis supplier with
# rules, sample products with categories (K1/K2/K3).
# ═══════════════════════════════════════════════════════════════════════

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import (
    Company,
    Product,
    ProductSupplierLink,
    Supplier,
    User,
)


async def seed() -> None:
    async with async_session_factory() as db:
        # ── Check if already seeded ──────────────────────────────────
        result = await db.execute(select(Company).limit(1))
        if result.scalar_one_or_none():
            print("✅ Database already seeded. Skipping.")
            return

        # ── 1. Demo Company ──────────────────────────────────────────
        company = Company(
            id=uuid.uuid4(),
            name="Ergalyon Demo ΕΠΕ",
            vat_number="EL099999999",
            settings_json={
                "timezone": "Europe/Athens",
                "currency": "EUR",
                "date_format": "DD/MM/YYYY",
            },
        )
        db.add(company)
        await db.flush()
        print(f"  ✔ Company: {company.name} ({company.id})")

        # ── 2. Admin User ────────────────────────────────────────────
        admin = User(
            id=uuid.uuid4(),
            company_id=company.id,
            email="admin@ergalyon.demo",
            # bcrypt hash for "admin123" — generated placeholder
            password_hash="$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1QlG4oHhJMZGwOhqRy3Xv3fG7pOe",
            role="admin",
            display_name="Διαχειριστής",
            is_active=True,
        )
        db.add(admin)
        await db.flush()
        print(f"  ✔ Admin user: {admin.email}")

        # ── 3. Poimenidis Supplier ──────────────────────────────────
        poimenidis = Supplier(
            id=uuid.uuid4(),
            company_id=company.id,
            name="Ποιμενίδης Α.Ε.",
            vat_number="EL094012345",
            tax_profile_json={
                "aade_afm": "094012345",
                "doy": "ΦΑΕ ΠΕΙΡΑΙΑ",
                "registration_status": "active",
                "activities": ["46730000-3", "46740000-0"],
            },
            contacts_json=[
                {
                    "name": "Γιώργος Ποιμενίδης",
                    "role": "Sales",
                    "phone": "+30 210 4123456",
                    "email": "sales@poimenidis.gr",
                }
            ],
            default_currency="EUR",
            default_parser="xml",
            rules_json={
                "code_normalization": [
                    {"op": "strip_prefix", "prefix": "03-"},
                    {"op": "trim"},
                ]
            },
            is_active=True,
        )
        db.add(poimenidis)
        await db.flush()
        print(f"  ✔ Supplier: {poimenidis.name}")

        # ── 4. Sample Products (with K1/K2/K3 category paths) ────────
        products_data = [
            # K1: Εργαλεία Χειρός → K2: Πριόνια → K3: Σπαθόσεγες
            Product(
                company_id=company.id,
                canonical_name="Σπαθόσεγα 300mm 18TPI",
                internal_code="ERG-00000001",
                technical_specs_json={
                    "blade_length": "300mm",
                    "teeth_per_inch": 18,
                    "material": "HSS",
                },
                category_path="Εργαλεία Χειρός/Πριόνια/Σπαθόσεγες",
                status="active",
            ),
            Product(
                company_id=company.id,
                canonical_name="Σπαθόσεγα 150mm 24TPI",
                internal_code="ERG-00000002",
                technical_specs_json={
                    "blade_length": "150mm",
                    "teeth_per_inch": 24,
                    "material": "Bi-Metal",
                },
                category_path="Εργαλεία Χειρός/Πριόνια/Σπαθόσεγες",
                status="active",
            ),
            # K1: Εργαλεία Χειρός → K2: Πριόνια → K3: Σέγες
            Product(
                company_id=company.id,
                canonical_name="Σέγα χειρός 450mm",
                internal_code="ERG-00000003",
                technical_specs_json={
                    "blade_length": "450mm",
                    "type": "hacksaw",
                },
                category_path="Εργαλεία Χειρός/Πριόνια/Σέγες",
                status="active",
            ),
            # K1: Ηλεκτρικά Εργαλεία → K2: Δράπανα → K3: Κατσαβίδια
            Product(
                company_id=company.id,
                canonical_name="Κατσαβίδι 18V Brushless 4Ah",
                internal_code="ERG-00000004",
                technical_specs_json={
                    "voltage": "18V",
                    "battery": "4Ah",
                    "type": "brushless",
                },
                category_path="Ηλεκτρικά Εργαλεία/Δράπανα/Κατσαβίδια",
                status="provisional",
            ),
            # K1: Ηλεκτρικά Εργαλεία → K2: Τριβεία → K3: Γωνιακοί Τροχοί
            Product(
                company_id=company.id,
                canonical_name="Γωνιακός Τροχός 125mm 1000W",
                internal_code="ERG-00000005",
                technical_specs_json={
                    "disc_diameter": "125mm",
                    "power": "1000W",
                    "rpm": 11000,
                },
                category_path="Ηλεκτρικά Εργαλεία/Τριβεία/Γωνιακοί Τροχοί",
                status="active",
            ),
        ]
        db.add_all(products_data)
        await db.flush()
        print(f"  ✔ {len(products_data)} products created")

        # ── 5. ProductSupplierLink (Poimenidis → Products) ───────────
        links = [
            ProductSupplierLink(
                company_id=company.id,
                product_id=products_data[0].id,
                supplier_id=poimenidis.id,
                supplier_sku_normalized="SAW-300-18",
                supplier_sku_raw_examples=["03-SAW-300-18", "SAW-300-18"],
                last_seen_at=None,
                price_history_json={
                    "current_price": 12.50,
                    "currency": "EUR",
                    "last_updated": "2026-06-01",
                },
            ),
            ProductSupplierLink(
                company_id=company.id,
                product_id=products_data[1].id,
                supplier_id=poimenidis.id,
                supplier_sku_normalized="SAW-150-24",
                supplier_sku_raw_examples=["03-SAW-150-24", "SAW-150-24"],
                last_seen_at=None,
                price_history_json={
                    "current_price": 8.90,
                    "currency": "EUR",
                    "last_updated": "2026-06-01",
                },
            ),
            ProductSupplierLink(
                company_id=company.id,
                product_id=products_data[2].id,
                supplier_id=poimenidis.id,
                supplier_sku_normalized="HACK-450",
                supplier_sku_raw_examples=["03-HACK-450", "HACK-450"],
                last_seen_at=None,
                price_history_json={
                    "current_price": 6.75,
                    "currency": "EUR",
                    "last_updated": "2026-05-15",
                },
            ),
            ProductSupplierLink(
                company_id=company.id,
                product_id=products_data[3].id,
                supplier_id=poimenidis.id,
                supplier_sku_normalized="DRILL-18V-BRUSH",
                supplier_sku_raw_examples=["03-DRILL-18V", "DRILL-18V-BRUSH"],
                last_seen_at=None,
                price_history_json={
                    "current_price": 89.00,
                    "currency": "EUR",
                    "last_updated": "2026-06-10",
                },
            ),
            ProductSupplierLink(
                company_id=company.id,
                product_id=products_data[4].id,
                supplier_id=poimenidis.id,
                supplier_sku_normalized="GRIND-125-1K",
                supplier_sku_raw_examples=["03-GRIND-125", "GRIND-125-1K"],
                last_seen_at=None,
                price_history_json={
                    "current_price": 45.50,
                    "currency": "EUR",
                    "last_updated": "2026-06-01",
                },
            ),
        ]
        db.add_all(links)
        await db.flush()
        print(f"  ✔ {len(links)} product-supplier links created")

        await db.commit()
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  ✅ Seed complete!                                      ║")
        print("║                                                         ║")
        print(f"║  Company:       {company.name:<30} ║")
        print(f"║  Admin email:   admin@ergalyon.demo                    ║")
        print(f"║  Supplier:      {poimenidis.name:<30} ║")
        print(f"║  Products:      {len(products_data)} created                              ║")
        print(f"║  SKU links:     {len(links)} created                              ║")
        print("╚══════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    asyncio.run(seed())
