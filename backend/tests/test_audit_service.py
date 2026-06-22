"""
Unit tests for Audit Service — tests the working internal helpers.
Note: log_event() has known parameter mismatches with the AuditLog model
(see report to user). Integration tests for log_event are deferred.
"""
import pytest
from uuid import uuid4
from decimal import Decimal

from app.services.audit_service import _convert_to_json_serializable


class TestConvertToJsonSerializable:
    """Test the JSON serialization helper (works correctly)."""

    def test_uuid_conversion(self):
        """UUID should be converted to string."""
        uid = uuid4()
        result = _convert_to_json_serializable(uid)
        assert result == str(uid)
        assert isinstance(result, str)

    def test_dict_with_uuids(self):
        """Dict with UUID values should be fully converted."""
        uid = uuid4()
        data = {"id": uid, "name": "test"}
        result = _convert_to_json_serializable(data)
        assert result["id"] == str(uid)
        assert result["name"] == "test"

    def test_nested_dict(self):
        """Nested dicts should be recursively converted."""
        uid = uuid4()
        data = {"outer": {"inner_id": uid}}
        result = _convert_to_json_serializable(data)
        assert result["outer"]["inner_id"] == str(uid)

    def test_list_conversion(self):
        """Lists should have each element converted."""
        uid1, uid2 = uuid4(), uuid4()
        result = _convert_to_json_serializable([uid1, uid2])
        assert result == [str(uid1), str(uid2)]

    def test_plain_values_passthrough(self):
        """Plain strings, ints, bools should pass through unchanged."""
        data = {"name": "test", "count": 42, "active": True}
        result = _convert_to_json_serializable(data)
        assert result == data

    def test_decimal_conversion(self):
        """Decimal should be converted to float."""
        data = {"price": Decimal("19.99")}
        result = _convert_to_json_serializable(data)
        assert result["price"] == 19.99
        assert isinstance(result["price"], float)
