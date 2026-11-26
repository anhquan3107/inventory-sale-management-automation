import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


REQUIRED_FIELDS = ("invoice_no", "sku", "quantity", "unit_price", "order_date", "sales_channel")
FIELDS = (*REQUIRED_FIELDS, "source_line_id")
MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50_000
MAX_COLUMNS = 64
MAX_CELL = 4096
MAX_IDENTIFIER = 160
MAX_QUANTITY = 1_000_000
MAX_AMOUNT = Decimal("9999999999.99")
TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    row: int | None = None
    field: str | None = None
    warning: bool = False


@dataclass(frozen=True)
class SalesLine:
    row: int
    sku: str
    product_id: int
    quantity: int
    unit_price: Decimal
    source_line_id: str

    @property
    def total(self) -> Decimal:
        return self.quantity * self.unit_price


@dataclass(frozen=True)
class Invoice:
    number: str
    order_date: datetime
    sales_channel: str
    lines: tuple[SalesLine, ...]

    @property
    def total(self) -> Decimal:
        return sum((line.total for line in self.lines), Decimal("0.00"))

    @property
    def fingerprint(self) -> str:
        lines = sorted(
            (line.sku, line.quantity, format(line.unit_price, ".2f"), line.source_line_id)
            for line in self.lines
        )
        payload = [1, self.number, self.order_date.isoformat(), self.sales_channel, lines]
        return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class ValidationResult:
    headers: tuple[str, ...]
    row_count: int
    invoices: tuple[Invoice, ...]
    issues: tuple[Issue, ...]

    @property
    def ready(self) -> bool:
        return bool(self.invoices) and not any(not issue.warning for issue in self.issues)


def validate_sales_csv(
    data: bytes,
    active_products: Mapping[str, int],
    mapping: Mapping[str, str] | None = None,
    *,
    now: datetime | None = None,
) -> ValidationResult:
    """Validate CSV bytes with an exact SKU-to-ID lookup for active catalog products.

    Mapping keys are canonical fields and values are exact CSV headers. Unspecified
    fields use their canonical headers. Identifiers are trimmed and case-sensitive.
    Issue row numbers refer to the first physical line of each CSV record.
    """
    headers: tuple[str, ...] = ()
    row_count = 0
    issues: list[Issue] = []
    groups: dict[str, list[tuple[datetime, str, SalesLine]]] = defaultdict(list)
    invoices: list[Invoice] = []

    def fail(code: str, message: str, row: int | None = None) -> ValidationResult:
        issues.append(Issue(code, message, row))
        return ValidationResult(headers, row_count, (), tuple(issues))

    if len(data) > MAX_BYTES:
        return fail("file_too_large", "Use a CSV file of at most 10 MiB.")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return fail("invalid_encoding", "Export the CSV as UTF-8.")
    if "\x00" in content:
        return fail("invalid_character", "Remove NUL characters from the CSV.")

    now = now if now is not None else datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError("now must include a UTC offset")

    reader = csv.reader(io.StringIO(content, newline=""), strict=True)
    try:
        headers = tuple(next(reader, ()))
        if (not headers or len(headers) > MAX_COLUMNS
                or any(not header.strip() or len(header) > MAX_CELL for header in headers)
                or len(set(headers)) != len(headers)):
            return fail("invalid_headers", "Use distinct, nonblank CSV headers within column and cell limits.", 1)

        if mapping is None:
            mapping = {}
        if not isinstance(mapping, Mapping) or any(
            field not in FIELDS or not isinstance(header, str) or header not in headers
            for field, header in mapping.items()
        ):
            return fail("invalid_mapping", "Map known canonical fields to existing CSV headers.")
        columns = {
            field: headers.index(mapping.get(field, field))
            for field in FIELDS if mapping.get(field, field) in headers
        }
        if len(set(columns.values())) != len(columns):
            return fail("duplicate_mapping", "Use each CSV column for at most one canonical field.")
        missing = [field for field in REQUIRED_FIELDS if field not in columns]
        if missing:
            return fail("missing_headers", f"Map the required fields: {', '.join(missing)}.")

        while True:
            row = reader.line_num + 1
            cells = next(reader, None)
            if cells is None:
                break
            row_count += 1
            if row_count > MAX_ROWS:
                return fail("too_many_rows", "Use a CSV with at most 50,000 data rows.", row)
            if len(cells) != len(headers) or any(len(cell) > MAX_CELL for cell in cells):
                issues.append(Issue("invalid_row_size", "Check column count and the 4,096-character cell limit.", row))
                continue
            values = {field: cells[index].strip() for field, index in columns.items()}
            parsed = _validate_row(values, row, active_products, now, issues)
            if parsed is not None:
                groups[values["invoice_no"]].append(parsed)
    except csv.Error:
        return fail("invalid_csv", "Check CSV quoting and field sizes.", max(reader.line_num, 1))

    if not row_count:
        return fail("empty_csv", "Include at least one historical sales row.")

    for number, records in groups.items():
        order_date, channel, first_line = records[0]
        lines = tuple(record[2] for record in records)
        if any((date, source_channel) != (order_date, channel) for date, source_channel, _ in records):
            issues.append(Issue("inconsistent_invoice", "Use the same timestamp and channel across all invoice rows.", first_line.row))
        line_ids: set[str] = set()
        seen_sales: dict[tuple[str, int, Decimal], SalesLine] = {}
        for line in lines:
            if line.source_line_id and line.source_line_id in line_ids:
                issues.append(Issue("duplicate_line_id", "Use a distinct source line ID for each invoice line.", line.row, "source_line_id"))
            if line.source_line_id:
                line_ids.add(line.source_line_id)
            key = (line.sku, line.quantity, line.unit_price)
            previous = seen_sales.get(key)
            if previous is not None and (not previous.source_line_id or not line.source_line_id):
                issues.append(Issue("ambiguous_line", "Verify repeated lines and provide distinct source line IDs.", line.row, "source_line_id"))
            seen_sales[key] = line
        invoice = Invoice(number, order_date, channel, lines)
        if invoice.total > MAX_AMOUNT:
            issues.append(Issue("invoice_total_overflow", "Invoice total exceeds the supported monetary range.", first_line.row))
        invoices.append(invoice)

    if any(not issue.warning for issue in issues):
        invoices.clear()
    return ValidationResult(headers, row_count, tuple(invoices), tuple(issues))


def _validate_row(
    values: dict[str, str],
    row: int,
    active_products: Mapping[str, int],
    now: datetime,
    issues: list[Issue],
) -> tuple[datetime, str, SalesLine] | None:
    start = len(issues)
    for field in ("invoice_no", "sku", "sales_channel", "source_line_id"):
        value = values.get(field, "")
        if len(value) > MAX_IDENTIFIER or (not value and field != "source_line_id"):
            issues.append(Issue("invalid_identifier", "Use a nonblank value of at most 160 characters.", row, field))

    product_id = active_products.get(values["sku"])
    if product_id is None and values["sku"]:
        issues.append(Issue("unknown_sku", "Use an exact active catalog SKU or correct the product mapping.", row, "sku"))

    quantity_text = values["quantity"]
    quantity = int(quantity_text) if re.fullmatch(r"[0-9]{1,7}", quantity_text) else 0
    if not 1 <= quantity <= MAX_QUANTITY:
        issues.append(Issue("invalid_quantity", "Use a whole quantity from 1 to 1,000,000. Returns are unsupported.", row, "quantity"))

    price = None
    price_text = values["unit_price"]
    if re.fullmatch(r"[0-9]{1,10}(?:\.[0-9]{1,2})?", price_text):
        price = Decimal(price_text).quantize(Decimal("0.01"))
        if price * quantity > MAX_AMOUNT:
            issues.append(Issue("line_total_overflow", "Line total exceeds the supported monetary range.", row, "unit_price"))
    else:
        issues.append(Issue("invalid_price", "Use a nonnegative price with up to ten whole digits and two decimal places.", row, "unit_price"))

    order_date = None
    timestamp = values["order_date"]
    if TIMESTAMP.fullmatch(timestamp) and not timestamp.endswith("-00:00"):
        try:
            order_date = datetime.fromisoformat(timestamp).astimezone(timezone.utc)
        except (ValueError, OverflowError):
            pass
    if order_date is None or order_date > now:
        issues.append(Issue("invalid_date", "Use a valid ISO timestamp with a known offset and no future date.", row, "order_date"))

    if price == 0:
        issues.append(Issue("zero_price", "Zero price accepted. Confirm this was a free item.", row, "unit_price", warning=True))
    if any(not issue.warning for issue in issues[start:]):
        return None
    assert product_id is not None and price is not None and order_date is not None
    return order_date, values["sales_channel"], SalesLine(
        row, values["sku"], product_id, quantity, price, values.get("source_line_id", ""),
    )
