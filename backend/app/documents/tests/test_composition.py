"""E01: commercial PDF composition from a fixed quotation snapshot."""

from decimal import Decimal
from io import BytesIO
import unittest

from pypdf import PdfReader

from backend.app.documents.composition import (
    GroupSchedule,
    QuotePdfSnapshot,
    compose_quote_pdf,
)


class QuotePdfCompositionTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = QuotePdfSnapshot(
            company="Expoclean",
            client="Ana Pérez",
            service_address="Av. Amazonas 123, Quito",
            scope="Limpieza general de oficinas y áreas comunes.",
            period="Semanal: 02/11/2026 - 08/11/2026",
            groups=(
                GroupSchedule(
                    spaces="8 oficinas de 35 m²",
                    days="lunes, miércoles y viernes",
                    visits_per_day=1,
                    hours="08:00 - 12:00",
                ),
                GroupSchedule(
                    spaces="2 salas de reunión",
                    days="martes y jueves",
                    visits_per_day=2,
                    hours="09:00 - 15:00",
                ),
            ),
            subtotal=Decimal("120.00"),
            tax=Decimal("18.00"),
            total=Decimal("138.00"),
        )

    def test_pdf_opens_and_contains_required_commercial_fields(self):
        pdf = compose_quote_pdf(self.snapshot)

        self.assertTrue(pdf.startswith(b"%PDF-"))
        reader = PdfReader(BytesIO(pdf))
        self.assertGreaterEqual(len(reader.pages), 1)
        text = "\n".join(page.extract_text() for page in reader.pages)
        for value in (
            "Expoclean",
            "Cliente",
            "Ana Pérez",
            "Dirección del servicio",
            "Av. Amazonas 123, Quito",
            "Alcance",
            "Limpieza general de oficinas y áreas comunes.",
            "Período",
            "Semanal: 02/11/2026 - 08/11/2026",
            "Calendario por grupo",
            "Subtotal",
            "USD 120.00",
            "Impuestos",
            "USD 18.00",
            "Total",
            "USD 138.00",
        ):
            with self.subTest(value=value):
                self.assertIn(value, text)

    def test_each_group_keeps_its_own_calendar(self):
        reader = PdfReader(BytesIO(compose_quote_pdf(self.snapshot)))
        text = "\n".join(page.extract_text() for page in reader.pages)

        for value in (
            "8 oficinas de 35 m²",
            "lunes, miércoles y viernes",
            "1 visita por día",
            "08:00 - 12:00",
            "2 salas de reunión",
            "martes y jueves",
            "2 visitas por día",
            "09:00 - 15:00",
        ):
            with self.subTest(value=value):
                self.assertIn(value, text)


if __name__ == "__main__":
    unittest.main()
