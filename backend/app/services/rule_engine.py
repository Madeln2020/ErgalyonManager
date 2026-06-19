# EDM v2 — Supplier Rule Engine Service (§8)

"""
Rule Engine για εφαρμογή supplier-specific κανόνων.

Τύποι κανόνων (§8.2):
  - code_normalization: strip_prefix, strip_suffix, regex_replace, pad_left, uppercase, trim
  - field_mapping: mapping custom πεδίων σε EDM fields
  - validation: format/required checks
  - enrichment_hint: υποδείξεις για scraping/enrichment
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional


@dataclass
class RuleResult:
    """Αποτέλεσμα εφαρμογής ενός rule."""
    field: str
    input_value: str
    output_value: str
    rule_type: str
    rule_id: Optional[str] = None
    confidence: float = 100.0
    triggered: bool = False
    error: Optional[str] = None


@dataclass
class NormalizedItem:
    """Κανονικοποιημένο invoice item μετά την εφαρμογή rules."""
    raw_supplier_code: str
    normalized_supplier_code: str
    raw_description: str
    normalized_description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    confidence: float
    rules_applied: list[RuleResult] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)


class RuleEngine:
    """
    Εφαρμόζει supplier-specific rules σε invoice items.

    Flow (§8.1):
      1. field_mapping → map columns/fields
      2. code_normalization → clean/transform codes
      3. validation → check format/required
      4. enrichment_hint → where to find specs
    """

    def __init__(self, rules_config: dict, supplier_id: str = None):
        """
        rules_config: το rules_json από τον supplier
        π.χ. {"code_normalization": [{"op": "strip_prefix", "prefix": "03-"}]}
        """
        self.rules = rules_config or {}
        self.supplier_id = supplier_id

    def normalize_item(
        self,
        raw_code: str,
        raw_description: str,
        quantity: Decimal,
        unit_price: Decimal,
        line_total: Decimal,
    ) -> NormalizedItem:
        """Εφαρμόζει όλους τους κανόνες σε ένα invoice item."""
        results: list[RuleResult] = []
        code = raw_code
        desc = raw_description
        conf = 100.0

        # 1. code_normalization
        code_rules = self.rules.get("code_normalization", [])
        for rule in code_rules:
            result = self._apply_code_normalization(code, rule)
            if result.triggered:
                code = result.output_value
                results.append(result)
                # Deterministic rules = 100% confidence
                result.confidence = 100.0

        # 2. field_mapping
        mapping = self.rules.get("field_mapping", {})
        if mapping:
            # field_mapping is used at parser level, not per-item
            pass

        # 3. validation
        validation_errors = []
        val_rules = self.rules.get("validation", [])
        for vrule in val_rules:
            errs = self._validate(vrule, code, desc)
            validation_errors.extend(errs)

        return NormalizedItem(
            raw_supplier_code=raw_code,
            normalized_supplier_code=code,
            raw_description=raw_description,
            normalized_description=desc,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
            confidence=conf,
            rules_applied=results,
            validation_errors=validation_errors,
        )

    def _apply_code_normalization(self, code: str, rule: dict) -> RuleResult:
        """Apply a single code_normalization operation."""
        ops = rule.get("operations", [rule])
        result = RuleResult(
            field="supplier_code",
            input_value=code,
            output_value=code,
            rule_type="code_normalization",
        )

        for op in ops:
            op_type = op.get("op", "")
            if op_type == "strip_prefix":
                prefix = op.get("prefix", "")
                if code.startswith(prefix):
                    code = code[len(prefix):]
                    result.triggered = True
            elif op_type == "trim":
                code = code.strip()
                if code != result.input_value:
                    result.triggered = True
            elif op_type == "uppercase":
                code = code.upper()
                result.triggered = True
            elif op_type == "strip_suffix":
                suffix = op.get("suffix", "")
                if code.endswith(suffix):
                    code = code[:len(suffix)]
                    result.triggered = True
            elif op_type == "regex_replace":
                pattern = op.get("pattern", "")
                replacement = op.get("replacement", "")
                new_code = re.sub(pattern, replacement, code)
                if new_code != code:
                    code = new_code
                    result.triggered = True
            elif op_type == "pad_left":
                length = int(op.get("length", 0))
                char = op.get("char", "0")
                if len(code) < length:
                    code = code.zfill(length)
                    result.triggered = True

        result.output_value = code
        return result

    def _validate(self, rule: dict, code: str, description: str) -> list[str]:
        """Run validation checks."""
        errors = []
        field = rule.get("field", "")
        rules_list = rule.get("rules", [])

        value = code if field == "normalized_supplier_code" else description

        for check in rules_list:
            if check.get("required") and not value:
                errors.append(f"{field}: required field is empty")
            if "regex" in check:
                pattern = check["regex"]
                if not re.match(pattern, value):
                    errors.append(f"{field}: does not match pattern {pattern}")

        return errors

    @staticmethod
    def get_poimenidis_rules() -> dict:
        """Προκαθορισμένοι κανόνες για Ποιμενίδη (§8.3)."""
        return {
            "code_normalization": [
                {
                    "operations": [
                        {"op": "strip_prefix", "prefix": "03-"},
                        {"op": "trim"},
                    ],
                    "description": "Poimenidis: 03-12345 → 12345 (deterministic, 100% confidence)",
                }
            ],
            "validation": [
                {
                    "field": "normalized_supplier_code",
                    "rules": [
                        {"required": True},
                        {"regex": "^[0-9]+$"},
                    ],
                }
            ],
            "enrichment_hint": {
                "manufacturer_code_source": "scraping",
                "scrape_url_template": "https://www.poimenidis.gr/search?q={supplier_code}",
            },
        }
