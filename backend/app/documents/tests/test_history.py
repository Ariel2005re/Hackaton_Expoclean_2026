"""E06–E07: historical search and retrieval use saved versions."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
import unittest

from pypdf import PdfReader

from backend.app.documents.composition import GroupSchedule, QuotePdfSnapshot
from backend.app.documents.history import HistoryService
from backend.app.documents.identity import VersionSnapshot
from backend.app.documents.issuance import EmissionService
from backend.app.documents.tests.test_issuance import FakeStore


class SearchableStore(FakeStore):
    def list_versions(self):
        return tuple(self.versions)

    def get_version(self, quote_id, code):
        return next(
            (
                version for version in self.versions
                if version.quote_id == quote_id and version.snapshot.code == code
            ),
            None,
        )


class HistoryServiceTests(unittest.TestCase):
    def _snapshot(self):
        quote = QuotePdfSnapshot(
            company="Expoclean",
            client="Ana Pérez",
            service_address="Av. Amazonas 123, Quito",
            scope="Limpieza de oficinas.",
            period="Semanal: 02/11/2026 - 08/11/2026",
            groups=(GroupSchedule("8 oficinas", "lunes", 1, "08:00 - 12:00"),),
            subtotal=Decimal("120.00"),
            tax=Decimal("18.00"),
            total=Decimal("138.00"),
        )
        return VersionSnapshot.from_quote_pdf(
            quote,
            {"tarifa_general": Decimal("7.13"), "margen": Decimal("20")},
            code="COT-001",
            issued_at=date(2026, 11, 1),
        )

    def test_find_old_version_by_code_client_and_service_after_configuration_change(self):
        store = SearchableStore()
        original = self._snapshot()
        emitted = EmissionService(store).emit(original, quote_id="draft-1")
        changed = replace(
            original,
            visible=replace(
                original.visible,
                client="Cliente Nuevo",
                service_address="Calle Nueva 99",
                scope="Limpieza especializada del hospital",
                total=Decimal("999.00"),
            ),
            price_values=(("tarifa_general", Decimal("99.00")),),
            code="COT-002",
            issued_at=date(2026, 11, 2),
        )
        EmissionService(store).emit(changed, quote_id="draft-1")
        history = HistoryService(store)

        for query in ("cot-001", "ANA PÉREZ", "amazonas", "oficinas"):
            with self.subTest(query=query):
                found = history.search(query)
                self.assertEqual([entry.code for entry in found], ["COT-001"])
                self.assertEqual(found[0].client, "Ana Pérez")
                self.assertEqual(found[0].total, Decimal("138.00"))

        self.assertEqual(history.download("draft-1", "COT-001"), emitted.pdf)
        self.assertEqual(history.search("no existe"), ())

    def test_download_requires_exact_quote_and_code_and_never_renders_again(self):
        store = SearchableStore()
        emitted = EmissionService(store).emit(self._snapshot(), quote_id="draft-1")
        history = HistoryService(store)

        self.assertIs(history.download("draft-1", "COT-001"), emitted.pdf)
        with self.assertRaises(LookupError):
            history.download("draft-2", "COT-001")
        with self.assertRaises(LookupError):
            history.download("draft-1", "COT-999")

    def test_controlled_snapshot_privacy_immutability_and_idempotency(self):
        store = SearchableStore()
        original = self._snapshot()
        original = replace(
            original,
            price_values=(("salario_secreto", Decimal("7777.77")),),
        )
        service = EmissionService(store)
        first = service.emit(original, quote_id="draft-1")
        changed = replace(
            original,
            visible=replace(original.visible, total=Decimal("184.00")),
            code="COT-002",
            issued_at=date(2026, 11, 2),
        )
        second = service.emit(changed, quote_id="draft-1")
        reverted = replace(original, code="COT-003", issued_at=date(2026, 11, 3))
        reused = service.emit(reverted, quote_id="draft-1")

        self.assertIs(reused, first)
        self.assertEqual(len(store.versions), 2)
        self.assertEqual([version.snapshot.code for version in store.versions], ["COT-001", "COT-002"])
        self.assertEqual(first.snapshot.issued_at, date(2026, 11, 1))
        self.assertEqual(first.snapshot.visible.total, Decimal("138.00"))
        self.assertEqual(second.snapshot.visible.total, Decimal("184.00"))
        old_pdf = HistoryService(store).download("draft-1", "COT-001")
        self.assertEqual(old_pdf, first.pdf)
        pdf_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(old_pdf)).pages)
        self.assertIn("USD 138.00", pdf_text)
        self.assertNotIn("USD 184.00", pdf_text)
        self.assertNotIn("7777.77", pdf_text)
        self.assertNotIn("salario_secreto", pdf_text)

    def test_failed_pdf_and_commit_leave_draft_and_history_untouched(self):
        original = self._snapshot()
        for failure in ("pdf", "commit"):
            with self.subTest(failure=failure):
                store = SearchableStore(fail_commit=failure == "commit")
                if failure == "pdf":
                    service = EmissionService(store, render_pdf=lambda _: (_ for _ in ()).throw(OSError("pdf")))
                else:
                    service = EmissionService(store)
                with self.assertRaises(OSError):
                    service.emit(original, quote_id="draft-1")
                self.assertEqual(store.draft, {"id": "draft-1", "status": "editable"})
                self.assertEqual(HistoryService(store).search(""), ())


if __name__ == "__main__":
    unittest.main()
