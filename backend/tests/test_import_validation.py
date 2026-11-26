import csv
import io
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from backend.app.services import import_validation as validation


NOW = datetime(2026, 11, 26, tzinfo=timezone.utc)
CATALOG = {"IMPORT-COF-001": 1, "IMPORT-TEA-001": 2}
ROWS = (
    ("000123", "IMPORT-COF-001", "2", "12.50", "2026-11-16T10:00:00Z", "ONLINE"),
    ("000123", "IMPORT-TEA-001", "1", "8.40", "2026-11-16T17:00:00+07:00", "ONLINE"),
    ("000124", "IMPORT-COF-001", "3", "12.50", "2026-11-18T11:00:00Z", "OFFLINE"),
)


def encode(rows, headers=validation.REQUIRED_FIELDS):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


class ImportValidationTests(unittest.TestCase):
    def validate(self, rows, headers=validation.REQUIRED_FIELDS, mapping=None):
        return validation.validate_sales_csv(encode(rows, headers), CATALOG, mapping, now=NOW)

    def test_canonical_fixture_and_fingerprint(self):
        result = self.validate(ROWS)
        self.assertTrue(result.ready)
        first, second = result.invoices
        self.assertEqual(result.row_count, 3)
        self.assertEqual(first.number, "000123")
        self.assertEqual(first.order_date.tzinfo, timezone.utc)
        self.assertEqual(first.total + second.total, Decimal("70.90"))
        self.assertEqual(first.fingerprint, self.validate(ROWS[:2][::-1]).invoices[0].fingerprint)
        changed = (*ROWS[0][:2], "3", *ROWS[0][3:])
        self.assertNotEqual(first.fingerprint, self.validate((changed, ROWS[1])).invoices[0].fingerprint)

    def test_mapping_quoted_values_and_zero_price_warning(self):
        headers = ("Invoice", *validation.REQUIRED_FIELDS[1:])
        row = (*ROWS[0][:3], "0", ROWS[0][4], 'In-store, "promotion"')
        result = self.validate((row,), headers, {"invoice_no": "Invoice"})
        self.assertTrue(result.ready)
        self.assertEqual(result.invoices[0].sales_channel, row[-1])
        self.assertEqual(result.issues[0].code, "zero_price")
        self.assertTrue(result.issues[0].warning)
        self.assertEqual(self.validate((row,), headers).issues[0].code, "missing_headers")
        self.assertEqual(self.validate((row,), headers, {"invoice_no": "sku"}).issues[0].code, "duplicate_mapping")

    def test_bad_row_blocks_entire_file(self):
        cases = (
            (1, "import-cof-001", "unknown_sku"),
            (2, "-1", "invalid_quantity"),
            (2, "1.5", "invalid_quantity"),
            (2, "1000001", "invalid_quantity"),
            (3, "NaN", "invalid_price"),
            (3, "1.001", "invalid_price"),
            (3, "9999999999.99", "line_total_overflow"),
            (4, "2026-11-16T10:00:00", "invalid_date"),
            (4, "2026-11-16T10:00:00+01:99", "invalid_date"),
            (4, "2026-12-01T10:00:00Z", "invalid_date"),
        )
        for index, value, code in cases:
            with self.subTest(value=value):
                row = list(ROWS[0])
                row[index] = value
                result = self.validate((row, ROWS[2]))
                self.assertFalse(result.ready)
                self.assertEqual(result.invoices, ())
                self.assertIn((code, 2), [(issue.code, issue.row) for issue in result.issues])

    def test_invoice_level_errors(self):
        result = self.validate((ROWS[0], (*ROWS[1][:-1], "OFFLINE")))
        self.assertEqual(result.issues[0].code, "inconsistent_invoice")
        result = self.validate((ROWS[0], ROWS[0]))
        self.assertEqual(result.issues[0].code, "ambiguous_line")
        rows = tuple((*row[:2], "1", "5000000000.00", *row[4:]) for row in ROWS[:2])
        self.assertEqual(self.validate(rows).issues[0].code, "invoice_total_overflow")
        result = self.validate(((*ROWS[0], "a"), (*ROWS[1], "a")), validation.FIELDS)
        self.assertEqual(result.issues[0].code, "duplicate_line_id")
        result = self.validate(((*ROWS[0], "a"), (*ROWS[0], "b")), validation.FIELDS)
        self.assertTrue(result.ready)
        self.assertEqual(len(result.invoices[0].lines), 2)

    def test_file_limits_and_malformed_csv(self):
        data = encode(ROWS)
        with patch.object(validation, "MAX_ROWS", 2):
            result = validation.validate_sales_csv(data, CATALOG, now=NOW)
            self.assertEqual(result.issues[0].code, "too_many_rows")
        with patch.object(validation, "MAX_BYTES", len(data) - 1):
            result = validation.validate_sales_csv(data, CATALOG, now=NOW)
            self.assertEqual(result.issues[0].code, "file_too_large")
        result = validation.validate_sales_csv(data + b'"unterminated', CATALOG, now=NOW)
        self.assertEqual(result.issues[0].code, "invalid_csv")
        result = self.validate(((*ROWS[0][:-1], "x" * 4097),))
        self.assertEqual(result.issues[0].code, "invalid_row_size")
