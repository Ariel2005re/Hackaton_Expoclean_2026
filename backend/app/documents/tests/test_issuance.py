"""E04 / RF-25–RF-27, RF-34: PDF and snapshot are issued together."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
import unittest

from pypdf import PdfReader

from backend.app.documents.composition import GroupSchedule, QuotePdfSnapshot
from backend.app.documents.identity import VersionSnapshot
from backend.app.documents.issuance import EmissionService, EmittedVersion


class FakeTransaction:
    def __init__(self, store):
        self.store = store
        self.pending = None

    def stage(self, quote_id, snapshot, pdf):
        self.pending = EmittedVersion(quote_id=quote_id, snapshot=snapshot, pdf=pdf)
        if self.store.fail_stage:
            raise OSError("storage refused staged version")

    def commit(self):
        self.store.versions.append(self.pending)
        if self.store.fail_commit:
            raise OSError("commit failed after tentative write")
        self.pending = None
        return self.store.versions[-1]

    def rollback(self):
        self.store.rollbacks += 1
        if self.pending in self.store.versions:
            self.store.versions.remove(self.pending)
        self.pending = None


class FakeStore:
    def __init__(self, *, fail_stage=False, fail_commit=False):
        self.draft = {"id": "draft-1", "status": "editable"}
        self.versions = []
        self.transactions = 0
        self.rollbacks = 0
        self.fail_stage = fail_stage
        self.fail_commit = fail_commit

    def find_by_identity(self, quote_id, identity):
        return next(
            (
                version
                for version in self.versions
                if version.quote_id == quote_id and version.snapshot.identity == identity
            ),
            None,
        )

    def begin(self):
        self.transactions += 1
        return FakeTransaction(self)


class EmissionServiceTests(unittest.TestCase):
    def setUp(self):
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
        self.snapshot = VersionSnapshot.from_quote_pdf(
            quote,
            {"tarifa_general": Decimal("7.13"), "margen": Decimal("20")},
            code="COT-001",
            issued_at=date(2026, 11, 1),
        )

    def test_success_persists_document_and_immutable_snapshot_together(self):
        store = FakeStore()

        issued = EmissionService(store).emit(self.snapshot, quote_id="draft-1")

        self.assertEqual(store.versions, [issued])
        self.assertIs(issued.snapshot, self.snapshot)
        self.assertTrue(issued.pdf.startswith(b"%PDF-"))
        text = PdfReader(BytesIO(issued.pdf)).pages[0].extract_text()
        self.assertIn("Ana Pérez", text)
        self.assertIn("USD 138.00", text)
        self.assertEqual(store.draft, {"id": "draft-1", "status": "editable"})
        self.assertEqual(store.rollbacks, 0)

    def test_pdf_failure_never_begins_persistence_or_changes_draft(self):
        store = FakeStore()

        def broken_renderer(_):
            raise RuntimeError("PDF generator unavailable")

        with self.assertRaisesRegex(RuntimeError, "PDF generator unavailable"):
            EmissionService(store, render_pdf=broken_renderer).emit(
                self.snapshot, quote_id="draft-1"
            )

        self.assertEqual(store.transactions, 0)
        self.assertEqual(store.versions, [])
        self.assertEqual(store.draft["status"], "editable")

    def test_unusable_pdf_is_not_persisted(self):
        store = FakeStore()

        with self.assertRaisesRegex(ValueError, "PDF"):
            EmissionService(store, render_pdf=lambda _: b"not a PDF").emit(
                self.snapshot, quote_id="draft-1"
            )

        self.assertEqual(store.transactions, 0)
        self.assertEqual(store.versions, [])
        self.assertEqual(store.draft["status"], "editable")

    def test_stage_failure_rolls_back_without_partial_version(self):
        store = FakeStore(fail_stage=True)

        with self.assertRaisesRegex(OSError, "staged version"):
            EmissionService(store).emit(self.snapshot, quote_id="draft-1")

        self.assertEqual(store.versions, [])
        self.assertEqual(store.rollbacks, 1)
        self.assertEqual(store.draft["status"], "editable")

    def test_commit_failure_rolls_back_tentative_version(self):
        store = FakeStore(fail_commit=True)

        with self.assertRaisesRegex(OSError, "commit failed"):
            EmissionService(store).emit(self.snapshot, quote_id="draft-1")

        self.assertEqual(store.versions, [])
        self.assertEqual(store.rollbacks, 1)
        self.assertEqual(store.draft["status"], "editable")

    def test_repeated_click_reuses_original_code_date_and_pdf(self):
        """E05 / RF-34: metadata proposed by a retry must not replace history."""
        store = FakeStore()
        original = EmissionService(store).emit(self.snapshot, quote_id="draft-1")
        retry = replace(self.snapshot, code="COT-999", issued_at=date(2026, 12, 1))

        def should_not_render(_):
            raise AssertionError("An equivalent version must reuse its saved PDF")

        reused = EmissionService(store, render_pdf=should_not_render).emit(
            retry, quote_id="draft-1"
        )

        self.assertIs(reused, original)
        self.assertEqual(reused.snapshot.code, "COT-001")
        self.assertEqual(reused.snapshot.issued_at, date(2026, 11, 1))
        self.assertEqual(reused.pdf, original.pdf)
        self.assertEqual(len(store.versions), 1)
        self.assertEqual(store.transactions, 1)

    def test_edit_then_revert_reuses_first_version_without_changing_newer_one(self):
        store = FakeStore()
        service = EmissionService(store)
        original = service.emit(self.snapshot, quote_id="draft-1")
        edited = replace(
            self.snapshot,
            visible=replace(self.snapshot.visible, scope="Limpieza de oficinas y patio."),
            code="COT-002",
            issued_at=date(2026, 11, 2),
        )
        newer = service.emit(edited, quote_id="draft-1")
        reverted = replace(self.snapshot, code="COT-003", issued_at=date(2026, 11, 3))

        reused = service.emit(reverted, quote_id="draft-1")

        self.assertIs(reused, original)
        self.assertIsNot(newer, original)
        self.assertEqual(newer.snapshot.code, "COT-002")
        self.assertEqual(len(store.versions), 2)
        self.assertEqual(store.versions, [original, newer])

    def test_price_input_change_creates_version_even_with_same_pdf_total(self):
        store = FakeStore()
        service = EmissionService(store)
        original = service.emit(self.snapshot, quote_id="draft-1")
        changed_prices = dict(self.snapshot.price_values)
        changed_prices["tarifa_general"] = Decimal("7.14")
        changed = replace(
            self.snapshot,
            price_values=tuple(sorted(changed_prices.items())),
            code="COT-002",
        )

        newer = service.emit(changed, quote_id="draft-1")

        self.assertIsNot(newer, original)
        self.assertNotEqual(newer.snapshot.identity, original.snapshot.identity)
        self.assertEqual(newer.snapshot.visible.total, original.snapshot.visible.total)
        self.assertEqual(store.versions, [original, newer])
        self.assertEqual(original.snapshot.code, "COT-001")

    def test_same_content_from_another_quote_does_not_reuse_version(self):
        store = FakeStore()
        service = EmissionService(store)
        first = service.emit(self.snapshot, quote_id="draft-1")

        second = service.emit(self.snapshot, quote_id="draft-2")

        self.assertIsNot(first, second)
        self.assertEqual(len(store.versions), 2)


if __name__ == "__main__":
    unittest.main()
