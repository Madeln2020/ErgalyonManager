#!/usr/bin/env python3
"""
Seed script to import suppliers from Ergalyon project into EDM v2
"""

import asyncio
import sys
from pathlib import Path

# Add the backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import our models
from app.models import Supplier, Organization

# Import DATABASE_URL from config
from app.config import settings
DATABASE_URL = str(settings.DATABASE_URL)

# SQLite connection for reading
import sqlite3

async def seed_suppliers():
    """Import suppliers from Ergalyon SQLite to EDM v2 PostgreSQL"""
    
    # Connect to Ergalyon SQLite DB
    ergalyon_db_path = "/home/admin/ergalyon/data/ergalyon.db"
    sqlite_conn = sqlite3.connect(ergalyon_db_path)
    sqlite_conn.row_factory = sqlite3.Row  # To access columns by name
    
    # Connect to EDM v2 PostgreSQL
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    print("🔌 Connected to databases")
    
    # Get default organization (first one)
    async with async_session() as session:
        result = await session.execute(select(Organization).limit(1))
        org = result.scalar_one_or_none()
        if org is None:
            print("❌ No organization found. Please create an organization first.")
            return
        organization_id = org.id
        print(f"🏢 Using organization: {org.name} (id={organization_id})")
    
    # Read suppliers from SQLite
    cursor = sqlite_conn.cursor()
    cursor.execute("""
        SELECT 
            id, name, code, supplier_type, pylon_supplier_code, 
            default_vat_rate, default_wholesale_markup, default_retail_markup, 
            default_unit, default_brand, brands, vat_number as afm, 
            address, contact_email, contact_phone, notes, language, country,
            is_active, created_at, updated_at
        FROM suppliers
    """)
    
    rows = cursor.fetchall()
    print(f"📊 Found {len(rows)} suppliers to import")
    
    imported = 0
    skipped = 0
    
    async with async_session() as session:
        for row in rows:
            # Check if supplier already exists (by name or code)
            result = await session.execute(
                select(Supplier).where(
                    (Supplier.name == row['name']) | 
                    (Supplier.code == row['code'])
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⏭️  Skipping existing: {row['name']}")
                skipped += 1
                continue
            
            # Determine status from is_active (1 = active, 0 = inactive)
            is_active_val = row['is_active']
            status_val = 'ACTIVE' if (is_active_val == 1) else 'INACTIVE'
            
            # Create new supplier
            supplier = Supplier(
                organization_id=organization_id,
                # Core fields
                name=row['name'] or "",
                code=row['code'] or None,
                supplier_type=row['supplier_type'] or None,
                pylon_supplier_code=row['pylon_supplier_code'] or None,
                
                # Contact & location
                afm=row['afm'] or None,
                address=row['address'] or None,
                country=row['country'] or "Greece",
                language=row['language'] or "Greek",
                
                # Financial defaults
                default_vat_rate=float(row['default_vat_rate']) if row['default_vat_rate'] else 24.0,
                default_unit=row['default_unit'] or "ΤΕΜ",
                default_wholesale_markup=float(row['default_wholesale_markup']) if row['default_wholesale_markup'] else 30.0,
                default_retail_markup=float(row['default_retail_markup']) if row['default_retail_markup'] else 55.0,
                
                # Branding
                brands=row['brands'] if row['brands'] else "[]",
                default_brand=row['default_brand'] or None,
                
                # Contact info
                contact_email=row['contact_email'] or None,
                contact_phone=row['contact_phone'] or None,
                notes=row['notes'] or None,
                
                # Status
                status=status_val,
                # deleted_at remains NULL (not soft deleted)
            )
            
            session.add(supplier)
            imported += 1
            print(f"✅ Imported: {row['name']} ({status_val})")
        
        await session.commit()
        print(f"\n🎉 Import complete: {imported} imported, {skipped} skipped")
    
    # Close connections
    sqlite_conn.close()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_suppliers())