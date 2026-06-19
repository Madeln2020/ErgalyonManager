# EDM v2 — Seed Script (development data)
# Creates sample supplier (Poimenidis) and categories

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import Category, Supplier, SupplierRule


async def seed():
    async with async_session_factory() as db:
        # Check if already seeded
        result = await db.execute(select(Supplier).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # ── Categories (§3.6) ──
        # K1
        k1 = Category(level=1, name="Εργαλεία Χειρός", code="TOOL-HAND")
        db.add(k1)
        await db.flush()

        # K2
        k2 = Category(level=2, name="Πριόνια", parent_id=k1.id, code="TOOL-HAND-SAW")
        db.add(k2)
        await db.flush()

        # K3
        k3 = Category(level=3, name="Σπαθόσεγες", parent_id=k2.id, code="TOOL-HAND-SAW-RECIP")
        k3b = Category(level=3, name="Σέγες", parent_id=k2.id, code="TOOL-HAND-SAW-HACK")
        db.add_all([k3, k3b])
        await db.flush()

        # More K1
        k1b = Category(level=1, name="Ηλεκτρικά Εργαλεία", code="TOOL-POWER")
        db.add(k1b)
        await db.flush()
        k2b = Category(level=2, name="Δράπανα", parent_id=k1b.id, code="TOOL-POWER-DRILL")
        k2c = Category(level=2, name="Τριβεία", parent_id=k1b.id, code="TOOL-POWER-GRIND")
        db.add_all([k2b, k2c])
        await db.flush()
        k3c = Category(level=3, name="Κατσαβίδια", parent_id=k2b.id, code="TOOL-POWER-DRILL-SCREW")
        k3d = Category(level=3, name="Γωνιακοί Τροχοί", parent_id=k2c.id, code="TOOL-POWER-GRIND-ANGLE")
        db.add_all([k3c, k3d])

        # ── Supplier: Poimenidis ──
        poimenidis = Supplier(
            name="Ποιμενίδης Α.Ε.",
            vat_number="094012345",
            parsing_profile="xml",
            rules_json={
                "code_normalization": [
                    {"op": "strip_prefix", "prefix": "03-"},
                    {"op": "trim"},
                ]
            },
        )
        db.add(poimenidis)
        await db.flush()

        # ── Supplier Rules (§8.3) ──
        rules = [
            SupplierRule(
                supplier_id=poimenidis.id,
                rule_type="code_normalization",
                priority=10,
                config_json={
                    "operations": [
                        {"op": "strip_prefix", "prefix": "03-"},
                        {"op": "trim"},
                    ],
                    "description": "Poimenidis: 03-12345 → 12345",
                },
            ),
            SupplierRule(
                supplier_id=poimenidis.id,
                rule_type="validation",
                priority=20,
                config_json={
                    "field": "normalized_supplier_code",
                    "rules": [{"required": True}, {"regex": "^[0-9]+$"}],
                },
            ),
        ]
        db.add_all(rules)

        await db.commit()
        print("✅ Seed complete: 1 supplier (Ποιμενίδης), 8 categories, 2 rules created.")


if __name__ == "__main__":
    asyncio.run(seed())
