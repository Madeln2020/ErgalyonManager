# EDM v2 — XML myDATA Parser Service (§9.3)

"""
Παράδειγμα myDATA XML structure:

<InvoicesDoc xmlns="http://www.aade.gr/myDATA/invoice/v1.0">
  <invoice>
    <invoiceHeader>
      <series>1</series>
      <aa>1234</aa>
      <issueDate>2026-06-15</issueDate>
      <invoiceTypeCode>1.1</invoiceTypeCode>
      <currency>EUR</currency>
    </invoiceHeader>
    <issuer>
      <vatNumber>094012345</vatNumber>
      <country>GR</country>
      <branch>0</branch>
    </issuer>
    <counterpart>
      <vatNumber>803034270</vatNumber>
      <country>GR</country>
    </counterpart>
    <invoiceDetails>
      <lineNumber>1</lineNumber>
      <itemCode>03-12345</itemCode>
      <itemDescr>ΠΕΡΙΓΡΑΦΗ</itemDescr>
      <quantity>2.000</quantity>
      <netValue>85.50</netValue>
      <vatCategory>1</vatCategory>
      <vatAmount>19.67</vatAmount>
    </invoiceDetails>
    <invoiceSummary>
      <totalNetValue>467.90</totalNetValue>
      <totalVatAmount>107.63</totalVatAmount>
      <totalGrossValue>575.53</totalGrossValue>
    </invoiceSummary>
  </invoice>
</InvoicesDoc>
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from lxml import etree

# myDATA XML namespace
NS = {"icls": "http://www.aade.gr/myDATA/invoice/v1.0"}


@dataclass
class ParsedInvoiceHeader:
    """Header information from an invoice."""
    invoice_number: str
    invoice_date: date
    currency: str = "EUR"
    issuer_vat: Optional[str] = None
    counterpart_vat: Optional[str] = None


@dataclass
class ParsedInvoiceLine:
    """Single line/item from an invoice."""
    line_number: int
    supplier_code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    vat_rate: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None


@dataclass
class ParsedInvoice:
    """Complete parsed invoice data."""
    header: ParsedInvoiceHeader
    lines: list[ParsedInvoiceLine] = field(default_factory=list)
    total_net: Optional[Decimal] = None
    total_vat: Optional[Decimal] = None
    total_gross: Optional[Decimal] = None
    parsing_confidence: float = 100.0
    file_format: str = "xml"


class XMLParser:
    """
    Parser for Greek myDATA (e-invoice) XML files.
    §9.3 — XML/myDATA parser, highest precedence source.
    Confidence: 99-100% for structured data.
    """

    def __init__(self, xml_content: bytes | str):
        if isinstance(xml_content, str):
            xml_content = xml_content.encode("utf-8")
        self.tree = etree.fromstring(xml_content)

    def parse_all(self) -> list[ParsedInvoice]:
        """Parse all invoices in the XML document."""
        invoices = []
        for invoice_elem in self.tree.xpath("//icls:invoice", namespaces=NS):
            parsed = self._parse_single(invoice_elem)
            if parsed:
                invoices.append(parsed)
        return invoices

    def _parse_single(self, invoice_elem) -> Optional[ParsedInvoice]:
        """Parse a single <invoice> element."""
        try:
            header = self._parse_header(invoice_elem)
            lines = self._parse_lines(invoice_elem)
            summary = self._parse_summary(invoice_elem)

            return ParsedInvoice(
                header=header,
                lines=lines,
                total_net=summary.get("total_net"),
                total_vat=summary.get("total_vat"),
                total_gross=summary.get("total_gross"),
            )
        except Exception as e:
            raise ValueError(f"Failed to parse invoice: {e}")

    def _parse_header(self, invoice_elem) -> ParsedInvoiceHeader:
        """Extract header fields."""
        xp = f"icls:invoiceHeader/"
        header = invoice_elem.find(f"icls:invoiceHeader", namespaces=NS)

        series = _txt(header, "icls:series")
        aa = _txt(header, "icls:aa")
        inv_num = f"{series}-{aa}" if series and aa else _txt(header, "icls:aa")

        date_str = _txt(header, "icls:issueDate")
        inv_date = date.fromisoformat(date_str) if date_str else date.today()

        currency = _txt(header, "icls:currency") or "EUR"

        # Issuer / Counterpart VAT
        issuer = invoice_elem.find("icls:issuer", namespaces=NS)
        counterpart = invoice_elem.find("icls:counterpart", namespaces=NS)
        issuer_vat = _txt(issuer, "icls:vatNumber") if issuer is not None else None
        counterpart_vat = _txt(counterpart, "icls:vatNumber") if counterpart is not None else None

        return ParsedInvoiceHeader(
            invoice_number=inv_num,
            invoice_date=inv_date,
            currency=currency,
            issuer_vat=issuer_vat,
            counterpart_vat=counterpart_vat,
        )

    def _parse_lines(self, invoice_elem) -> list[ParsedInvoiceLine]:
        """Extract invoice detail lines."""
        lines = []
        for detail in invoice_elem.xpath("icls:invoiceDetails", namespaces=NS):
            line = self._parse_line(detail)
            if line:
                lines.append(line)
        return lines

    def _parse_line(self, detail) -> Optional[ParsedInvoiceLine]:
        """Extract a single invoice line."""
        code = _txt(detail, "icls:itemCode") or ""
        desc = _txt(detail, "icls:itemDescr") or ""
        qty_str = _txt(detail, "icls:quantity") or "0"
        net_str = _txt(detail, "icls:netValue") or "0"

        line_num_str = _txt(detail, "icls:lineNumber")
        line_num = int(line_num_str) if line_num_str else 0

        qty = _dec(qty_str, 3)
        net = _dec(net_str, 2)
        unit_price = (net / qty).quantize(Decimal("0.01")) if qty > 0 else Decimal("0")

        vat_amt_str = _txt(detail, "icls:vatAmount")
        vat_amt = _dec(vat_amt_str) if vat_amt_str else None

        return ParsedInvoiceLine(
            line_number=line_num,
            supplier_code=code.strip(),
            description=desc.strip(),
            quantity=qty,
            unit_price=unit_price,
            line_total=net,
            vat_amount=vat_amt,
        )

    def _parse_summary(self, invoice_elem) -> dict:
        """Extract invoice summary totals."""
        summary = invoice_elem.find("icls:invoiceSummary", namespaces=NS)
        if summary is None:
            return {}
        return {
            "total_net": _dec(_txt(summary, "icls:totalNetValue")),
            "total_vat": _dec(_txt(summary, "icls:totalVatAmount")),
            "total_gross": _dec(_txt(summary, "icls:totalGrossValue")),
        }


# ── Helpers ──

def _txt(elem, xpath: str) -> Optional[str]:
    """Get text content from a child element."""
    if elem is None:
        return None
    child = elem.find(xpath, namespaces=NS)
    return child.text.strip() if child is not None and child.text else None


def _dec(val: Optional[str], precision: int = 2) -> Decimal:
    """Safely convert string to Decimal."""
    if not val:
        return Decimal("0")
    try:
        return Decimal(val).quantize(Decimal(f"0.{'0' * precision}"))
    except Exception:
        return Decimal("0")
