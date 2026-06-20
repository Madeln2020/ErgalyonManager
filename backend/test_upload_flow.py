#!/usr/bin/env python3
"""
EDM v2.1 — Phase 4: Invoice Intake — Minimal Integration Test

This script tests the upload flow without requiring full setup:
1. Upload a test file
2. Check status
3. Verify parse result

Usage: python test_upload_flow.py
"""
import asyncio
import hashlib
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Company, Supplier, InboundFile, User
from app.services.minio_client import upload_bytes, ensure_bucket_exists, download_bytes, RAW_UPLOADS_BUCKET
from app.services.parse_document_service import parse_document_sync
from app.routers.upload import _get_ext, _validate_file, _compute_sha256
from uuid import uuid4

MINIO_BUCKET = "raw-uploads"


async def test_minio():
    """Test MinIO connection and bucket creation."""
    print("\n=== Test 1: MinIO Connection ===")
    try:
        ensure_bucket_exists()
        print(f"✓ MinIO bucket '{MINIO_BUCKET}' is ready")
        return True
    except Exception as e:
        print(f"✗ MinIO connection failed: {e}")
        return False


def test_file_validation():
    """Test file validation logic."""
    print("\n=== Test 2: File Validation ===")

    # Valid files
    valid_files = [
        ("test.pdf", b"%PDF-1.4\n% test"),
        ("test.xml", b"<?xml version=\"1.0\"?>\n<root/>"),
        ("test.xlsx", b"PK\x03\x04"),
        ("test.png", b"\x89PNG\r\n\x1a\n"),
        ("test.jpg", b"\xff\xd8\xff\xe0"),
    ]

    for filename, content in valid_files:
        try:
            ext, file_type = _validate_file(filename, content)
            print(f"✓ {filename} ({ext}) -> {file_type}")
        except Exception as e:
            print(f"✗ {filename} validation failed: {e}")
            return False

    # Invalid files
    invalid_files = [
        ("test.exe", b"MZ"),
        ("test.txt", b"text"),
    ]

    for filename, content in invalid_files:
        try:
            _validate_file(filename, content)
            print(f"✗ {filename} should have been rejected")
            return False
        except Exception:
            print(f"✓ {filename} correctly rejected")

    return True


def test_sha256():
    """Test SHA256 computation."""
    print("\n=== Test 3: SHA256 Computation ===")
    test_data = b"test data for sha256"
    sha256 = _compute_sha256(test_data)
    expected = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    if sha256 == expected:
        print(f"✓ SHA256 matches: {sha256}")
        return True
    else:
        print(f"✗ SHA256 mismatch: got {sha256}, expected {expected}")
        return False


async def test_upload_flow():
    """Test the complete upload flow."""
    print("\n=== Test 4: Upload Flow ===")

    # Create test data
    test_content = b"test invoice content"
    filename = "test_invoice.xml"
    sha256 = _compute_sha256(test_content)

    # Test upload to MinIO
    try:
        object_key = f"test_supplier/{uuid4()}{_get_ext(filename)}"
        upload_bytes(test_content, object_key, bucket=MINIO_BUCKET)
        print(f"✓ File uploaded to MinIO: {object_key}")

        # Test download
        downloaded = download_bytes(object_key, bucket=MINIO_BUCKET)
        if downloaded == test_content:
            print(f"✓ File downloaded successfully")
        else:
            print(f"✗ Downloaded content mismatch")
            return False

        return True
    except Exception as e:
        print(f"✗ Upload flow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_parse_service():
    """Test the parse document service."""
    print("\n=== Test 5: Parse Document Service ===")

    # Test XML parsing
    test_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<InvoicesDoc xmlns="http://www.aade.gr/myDATA/invoice/v1.0">
  <invoice>
    <invoiceHeader>
      <series>1</series>
      <aa>1234</aa>
      <issueDate>2026-06-15</issueDate>
      <invoiceTypeCode>1.1</invoiceTypeCode>
      <currency>EUR</currency>
    </invoiceHeader>
    <invoiceDetails>
      <lineNumber>1</lineNumber>
      <itemCode>03-12345</itemCode>
      <itemDescr>Test Item</itemDescr>
      <quantity>2.000</quantity>
      <netValue>10.00</netValue>
      <vatCategory>1</vatCategory>
      <vatAmount>1.90</vatAmount>
    </invoiceDetails>
  </invoice>
</InvoicesDoc>"""

    try:
        result = parse_document_sync(test_xml, "xml")
        print(f"✓ XML parsed successfully")
        print(f"  - Doc kind: {result.doc_kind}")
        print(f"  - Confidence: {result.confidence}")
        print(f"  - Lines found: {len(result.lines)}")
        if result.lines:
            print(f"  - First line: {result.lines[0]}")
        if result.error_message:
            print(f"  - Error: {result.error_message}")
        return True
    except Exception as e:
        print(f"✗ XML parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("EDM v2.1 — Phase 4: Invoice Intake — Integration Test")
    print("=" * 60)

    results = []

    # Test MinIO
    results.append(("MinIO Connection", await test_minio()))

    # Test file validation
    results.append(("File Validation", test_file_validation()))

    # Test SHA256
    results.append(("SHA256 Computation", test_sha256()))

    # Test upload flow
    results.append(("Upload Flow", await test_upload_flow()))

    # Test parse service
    results.append(("Parse Service", await test_parse_service()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)
    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
