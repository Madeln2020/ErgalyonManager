#!/bin/bash
# Test script for Phase 3: Supplier Management and JWT Auth
# Uses Python to validate imports and check syntax

cd /home/admin/edm-v2/backend

echo "=== Validating Python imports ==="
python3 -c "
from app.models import Supplier, User, Company
from app.schemas import SupplierCreate, SupplierRead, SupplierUpdate, SupplierListRead, UserRead
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.auth import Role, require_role, get_current_user, create_access_token, hash_password, verify_password
from app.services.aade_service import fetch_tax_profile_from_aade, fetch_tax_profile_for_supplier
from app.config import settings

print('✓ All imports successful')
print(f'✓ Settings: APP_NAME={settings.APP_NAME}, ALGORITHM={settings.ALGORITHM}')
print(f'✓ ACCESS_TOKEN_EXPIRE_MINUTES={settings.ACCESS_TOKEN_EXPIRE_MINUTES}')
print(f'✓ Role hierarchy: {list(Role)}')
print(f'✓ Auth imports: get_current_user, require_role, create_access_token, hash_password all available')
"

echo ""
echo "=== Checking model fields ==="
python3 -c "
from app.models import Supplier
from sqlalchemy import inspect
import sys

# Check Supplier model columns
cols = Supplier.__table__.columns
col_names = [c.name for c in cols]
expected = ['id', 'company_id', 'name', 'vat_number', 'tax_profile_json', 
            'contacts_json', 'default_currency', 'default_parser', 'rules_json',
            'is_active', 'is_deleted', 'created_at', 'updated_at']
missing = [c for c in expected if c not in col_names]
extra = [c for c in col_names if c not in expected and not c.startswith('_')]
if missing:
    print(f'✗ Missing columns: {missing}')
    sys.exit(1)
if extra:
    print(f'⚠ Extra columns: {extra}')
print(f'✓ All expected columns present: {expected}')
"

echo ""
echo "=== Checking unique constraints ==="
python3 -c "
from app.models import Supplier
constraints = [c for c in Supplier.__table__.constraints]
uc_name = None
for c in constraints:
    if hasattr(c, 'name') and 'uq_company_vat' in str(c.name):
        uc_name = c.name
        break
if uc_name:
    print(f'✓ Unique constraint on (company_id, vat_number): {uc_name}')
else:
    print('✗ Missing unique constraint on (company_id, vat_number)')
    import sys; sys.exit(1)
"

echo ""
echo "=== Checking service imports ==="
python3 -c "
from app.services.supplier_service import create_supplier, get_supplier, list_suppliers, update_supplier, delete_supplier
print('✓ Supplier service functions importable')
from app.services.aade_service import fetch_tax_profile_from_aade, fetch_tax_profile_for_supplier
print('✓ AADE service functions importable')
"

echo ""
echo "=== Checking router imports ==="
python3 -c "
from app.routers.suppliers import router as supplier_router
from app.routers.auth import router as auth_router
print(f'✓ Supplier router: {len(supplier_router.routes)} routes')
print(f'✓ Auth router: {len(auth_router.routes)} routes')
"

echo ""
echo "=== Checking user role constraint ==="
python3 -c "
from app.models import User
from sqlalchemy import CheckConstraint
checks = [c for c in User.__table__.constraints if isinstance(c, CheckConstraint)]
role_checks = [str(c) for c in checks if 'role' in str(c).lower()]
if role_checks:
    print(f'✓ User role CheckConstraint found: {role_checks}')
    # Verify it contains 'owner'
    if 'owner' in str(role_checks[0]).lower():
        print('✓ Role constraint includes owner')
    else:
        print('⚠ Role constraint may be missing owner')
else:
    print('✗ No role CheckConstraint found')
"

echo ""
echo "=== Done ==="