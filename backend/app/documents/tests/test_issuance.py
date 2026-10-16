"""E04 / RF-25–RF-27, RF-34: PDF and snapshot are issued together."""

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

    def stage(self, snapshot, pdf):
        self.pending = EmittedVersion(snapshot=snapshot, pdf=pdf)
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

        issued = EmissionService(store).emit(self.snapshot)

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
            EmissionService(store, render_pdf=broken_renderer).emit(self.snapshot)

        self.assertEqual(store.transactions, 0)
        self.assertEqual(store.versions, [])
        self.assertEqual(store.draft["status"], "editable")

    def test_unusable_pdf_is_not_persisted(self):
        store = FakeStore()

        with self.assertRaisesRegex(ValueError, "PDF"):
            EmissionService(store, render_pdf=lambda _: b"not a PDF").emit(self.snapshot)

        self.assertEqual(store.transactions, 0)
        self.assertEqual(store.versions, [])
        self.assertEqual(store.draft["status"], "editable")

    def test_stage_failure_rolls_back_without_partial_version(self):
        store = FakeStore(fail_stage=True)

        with self.assertRaisesRegex(OSError, "staged version"):
            EmissionService(store).emit(self.snapshot)

        self.assertEqual(store.versions, [])
        self.assertEqual(store.rollbacks, 1)
        self.assertEqual(store.draft["status"], "editable")

    def test_commit_failure_rolls_back_tentative_version(self):
        store = FakeStore(fail_commit=True)

        with self.assertRaisesRegex(OSError, "commit failed"):
            EmissionService(store).emit(self.snapshot)

        self.assertEqual(store.versions, [])
        self.assertEqual(store.rollbacks, 1)
        self.assertEqual(store.draft["status"], "editable")


if __name__ == "__main__":
    unittest.main()
