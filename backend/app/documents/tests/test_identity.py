"""E03 / RF-25, RF-34: identity of emitted quotation content."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
import unittest

from backend.app.documents.composition import GroupSchedule, QuotePdfSnapshot
from backend.app.documents.identity import VersionSnapshot


class VersionIdentityTests(unittest.TestCase):
    def setUp(self):
        self.quote = QuotePdfSnapshot(
            company="Expoclean",
            client="Ana Pérez",
            service_address="Av. Amazonas 123, Quito",
            scope="Limpieza general de oficinas.",
            period="Semanal: 02/11/2026 - 08/11/2026",
            groups=(
                GroupSchedule("8 oficinas", "lunes y miércoles", 1, "08:00 - 12:00"),
            ),
            subtotal=Decimal("120.00"),
            tax=Decimal("18.00"),
            total=Decimal("138.00"),
        )
        self.price_values = {
            "mano_obra.general.tarifa_hora": Decimal("7.13"),
            "factor_estado": Decimal("1.25"),
            "margen_porcentaje": Decimal("20.00"),
            "descuento_fijo": Decimal("0.00"),
        }

    def snapshot(self, quote=None, price_values=None, code="COT-001", issued_at=None):
        return VersionSnapshot.from_quote_pdf(
            quote or self.quote,
            price_values if price_values is not None else self.price_values,
            code=code,
            issued_at=issued_at or date(2026, 11, 1),
        )

    def test_equivalent_content_ignores_version_code_date_and_mapping_order(self):
        first = self.snapshot()
        same_content = self.snapshot(
            price_values=dict(reversed(list(self.price_values.items()))),
            code="COT-099",
            issued_at=date(2026, 12, 15),
        )
        self.assertEqual(first.identity, same_content.identity)
        self.assertEqual(len(first.identity), 64)

    def test_visible_changes_create_a_different_identity(self):
        original = self.snapshot()
        changed_quotes = (
            replace(self.quote, service_address="Otra dirección, Quito"),
            replace(self.quote, subtotal=Decimal("121.00")),
            replace(
                self.quote,
                groups=(replace(self.quote.groups[0], days="martes"),),
            ),
        )
        for quote in changed_quotes:
            with self.subTest(quote=quote):
                self.assertNotEqual(original.identity, self.snapshot(quote=quote).identity)

    def test_price_input_change_creates_a_different_identity_even_if_total_stays(self):
        original = self.snapshot()
        changed_values = dict(self.price_values)
        changed_values["mano_obra.general.tarifa_hora"] = Decimal("7.14")

        self.assertEqual(original.visible.total, self.snapshot(price_values=changed_values).visible.total)
        self.assertNotEqual(original.identity, self.snapshot(price_values=changed_values).identity)

    def test_snapshot_copies_price_values_and_canonicalizes_equal_decimals(self):
        source = dict(self.price_values)
        first = self.snapshot(price_values=source)
        source["factor_estado"] = Decimal("1.50")
        equivalent = dict(self.price_values)
        equivalent["factor_estado"] = Decimal("1.250")
        equivalent["descuento_fijo"] = Decimal("0")

        self.assertEqual(first.identity, self.snapshot(price_values=equivalent).identity)
        self.assertNotEqual(first.identity, self.snapshot(price_values=source).identity)


if __name__ == "__main__":
    unittest.main()
