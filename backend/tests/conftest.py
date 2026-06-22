"""
Test configuration and fixtures for EDM v2.1 test suite.
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://edm:edm_password@localhost:5432/edm_v2"


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    # Import Base here to avoid circular imports
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test using transaction rollback."""
    connection = await test_engine.connect()
    transaction = await connection.begin()
    async_session = async_sessionmaker(
        bind=connection, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Begin a nested transaction (SAVEPOINT)
        nested = await connection.begin_nested()
        
        # If the application code calls session.commit, 
        # we'll end up here since the nested transaction won't actually commit
        # (it's just a savepoint) and we'll need to start a new nested transaction
        # when the session tries to commit
        if hasattr(session, '_nested'):
            session._nested = nested
        else:
            session._nested = nested
            
        yield session
        
        # Roll back the nested transaction, leaving the session as it was
        # before the test ran
        if nested.is_active:
            await nested.rollback()
    
    # Clean up: rollback the outer transaction and close the connection
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def test_company(db_session: AsyncSession):
    """Sample company data for tests."""
    from app.models import Company
    company_data = {
        "id": uuid4(),
        "name": "Test Company",
        "vat_number": "123456789",
        "settings_json": {},
    }
    company = Company(**company_data)
    db_session.add(company)
    await db_session.flush()
    return company


@pytest_asyncio.fixture
async def test_supplier(db_session: AsyncSession, test_company):
    """Sample supplier data for tests."""
    from app.models import Supplier
    supplier_data = {
        "id": uuid4(),
        "name": "Test Supplier",
        "vat_number": "987654321",
        "default_currency": "EUR",
        "is_active": True,
        "rules_json": {
            "code_normalization": [{"op": "strip_prefix", "prefix": "03-"}],
            "validation": [],
        },
        "company_id": test_company.id,  # Added required foreign key
    }
    supplier = Supplier(**supplier_data)
    db_session.add(supplier)
    await db_session.flush()
    return supplier


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, test_company):
    """Sample product data for tests."""
    from app.models import Product
    product_data = {
        "id": uuid4(),
        "canonical_name": "Test Product",
        "internal_code": "INT-001",
        "category_path": "Test > Category",
        "status": "active",
        "technical_specs_json": {},
        "is_deleted": False,
        "company_id": test_company.id,  # Use the actual company id from the inserted company
    }
    product = Product(**product_data)
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_company):
    """Sample user data for tests."""
    from app.models import User
    user_data = {
        "id": uuid4(),
        "email": "test@example.com",
        "password_hash": "$2b$12$hashedpassword",  # dummy hash
        "display_name": "Test User",
        "role": "admin",
        "company_id": test_company.id,  # Use the actual company id from the inserted company
        "is_active": True,
    }
    user = User(**user_data)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_product_supplier_link(db_session: AsyncSession, test_product, test_supplier, test_company):
    """Sample product-supplier link for tests."""
    from app.models import ProductSupplierLink
    link_data = {
        "id": uuid4(),
        "company_id": test_company.id,
        "product_id": test_product.id,
        "supplier_id": test_supplier.id,
        "supplier_sku_normalized": "TEST-SKU-001",
        "price_history_json": [],
    }
    link = ProductSupplierLink(**link_data)
    db_session.add(link)
    await db_session.flush()
    return link
