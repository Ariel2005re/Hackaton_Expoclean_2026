"""E04: render and store a PDF with its version snapshot atomically.

The storage adapter implements the transaction boundary. A real database
adapter must keep staged data invisible until commit and undo tentative writes
when rollback is called, including after a failed commit.
"""

from dataclasses import dataclass
from typing import Callable, Protocol

from .composition import QuotePdfSnapshot, compose_quote_pdf
from .identity import VersionSnapshot


@dataclass(frozen=True)
class EmittedVersion:
    snapshot: VersionSnapshot
    pdf: bytes


class VersionTransaction(Protocol):
    def stage(self, snapshot: VersionSnapshot, pdf: bytes) -> None: ...

    def commit(self) -> EmittedVersion: ...

    def rollback(self) -> None: ...


class VersionStore(Protocol):
    def begin(self) -> VersionTransaction: ...


class EmissionService:
    def __init__(
        self,
        store: VersionStore,
        render_pdf: Callable[[QuotePdfSnapshot], bytes] = compose_quote_pdf,
    ) -> None:
        self._store = store
        self._render_pdf = render_pdf

    def emit(self, snapshot: VersionSnapshot) -> EmittedVersion:
        """Persist a complete version or leave the draft with no new version."""
        pdf = self._render_pdf(snapshot.visible.to_pdf_snapshot())
        if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-"):
            raise ValueError("La generación no devolvió un PDF válido")

        transaction = self._store.begin()
        try:
            transaction.stage(snapshot, pdf)
            return transaction.commit()
        except Exception:
            transaction.rollback()
            raise
