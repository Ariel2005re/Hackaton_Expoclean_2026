"""E04: render and store a PDF with its version snapshot atomically.

The storage adapter implements the transaction boundary. A real database
adapter must keep staged data invisible until commit and undo tentative writes
when rollback is called, including after a failed commit.
"""

from dataclasses import dataclass
from io import BytesIO
from typing import Callable, Protocol
from pypdf import PdfReader

from .composition import QuotePdfSnapshot, compose_quote_pdf
from .identity import VersionSnapshot


@dataclass(frozen=True)
class EmittedVersion:
    quote_id: str
    snapshot: VersionSnapshot
    pdf: bytes


class VersionTransaction(Protocol):
    def stage(self, quote_id: str, snapshot: VersionSnapshot, pdf: bytes) -> None: ...

    def commit(self) -> EmittedVersion: ...

    def rollback(self) -> None: ...


class VersionStore(Protocol):
    def find_by_identity(self, quote_id: str, identity: str) -> EmittedVersion | None: ...

    def begin(self) -> VersionTransaction: ...


class EmissionService:
    def __init__(
        self,
        store: VersionStore,
        render_pdf: Callable[[QuotePdfSnapshot], bytes] = compose_quote_pdf,
    ) -> None:
        self._store = store
        self._render_pdf = render_pdf

    def emit(self, snapshot: VersionSnapshot, *, quote_id: str) -> EmittedVersion:
        """Reuse equivalent history or persist a complete new version."""
        if not quote_id:
            raise ValueError("La cotización requiere un identificador")

        existing = self._store.find_by_identity(quote_id, snapshot.identity)
        if existing is not None:
            return existing

        pdf = self._render_pdf(snapshot.visible.to_pdf_snapshot(
            code=snapshot.code, issued_at=snapshot.issued_at,
        ))
        if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-"):
            raise ValueError("La generación no devolvió un PDF válido")
        try:
            reader = PdfReader(BytesIO(pdf), strict=True)
            if not reader.pages:
                raise ValueError("El PDF no contiene páginas")
            for page in reader.pages:
                page.get_contents()
        except Exception as exc:
            raise ValueError("La generación no devolvió un PDF recuperable") from exc

        transaction = self._store.begin()
        try:
            transaction.stage(quote_id, snapshot, pdf)
            return transaction.commit()
        except Exception:
            transaction.rollback()
            raise
