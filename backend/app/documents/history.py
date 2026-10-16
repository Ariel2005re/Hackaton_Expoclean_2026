"""E06 / RF-27–RF-28: find emitted versions and return their saved PDFs."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from .issuance import EmittedVersion


@dataclass(frozen=True)
class HistoryEntry:
    quote_id: str
    code: str
    issued_at: date
    client: str
    service_address: str
    scope: str
    total: Decimal


class HistoryStore(Protocol):
    def list_versions(self) -> tuple[EmittedVersion, ...]: ...

    def get_version(self, quote_id: str, code: str) -> EmittedVersion | None: ...


class HistoryService:
    def __init__(self, store: HistoryStore) -> None:
        self._store = store

    def search(self, query: str) -> tuple[HistoryEntry, ...]:
        """Search saved version fields, independent of the current draft."""
        term = query.strip().casefold()
        matches = []
        for version in self._store.list_versions():
            snapshot = version.snapshot
            fields = (
                snapshot.code,
                snapshot.visible.client,
                snapshot.visible.service_address,
                snapshot.visible.scope,
            )
            if any(term in field.casefold() for field in fields):
                matches.append(
                    HistoryEntry(
                        quote_id=version.quote_id,
                        code=snapshot.code,
                        issued_at=snapshot.issued_at,
                        client=snapshot.visible.client,
                        service_address=snapshot.visible.service_address,
                        scope=snapshot.visible.scope,
                        total=snapshot.visible.total,
                    )
                )
        return tuple(matches)

    def download(self, quote_id: str, code: str) -> bytes:
        """Return the document persisted for this exact quote and version."""
        version = self._store.get_version(quote_id, code)
        if version is None:
            raise LookupError("No existe una versión emitida con ese código")
        return version.pdf
