"""PostgreSQL-backed immutable PDF versions (RF-25–RF-28, RF-34)."""

from datetime import datetime, time
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.ia_versiones import VersionCotizacion
from backend.app.documents.composition import GroupSchedule, QuotePdfSnapshot
from backend.app.documents.identity import VersionSnapshot
from backend.app.documents.issuance import EmittedVersion


def _snapshot_from_row(row: VersionCotizacion) -> VersionSnapshot:
    saved = row.datos_inmutables
    visible = saved["visible"]
    pdf_snapshot = QuotePdfSnapshot(
        company=visible["company"], client=visible["client"],
        service_address=visible["service_address"], scope=visible["scope"],
        period=visible["period"],
        groups=tuple(GroupSchedule(**g) for g in visible["groups"]),
        subtotal=Decimal(visible["subtotal"]), tax=Decimal(visible["tax"]),
        total=Decimal(visible["total"]),
    )
    return VersionSnapshot.from_quote_pdf(
        pdf_snapshot,
        {k: Decimal(v) for k, v in saved["price_values"].items()},
        code=row.id, issued_at=row.fecha_emision.date(),
    )


def _emitted(row: VersionCotizacion) -> EmittedVersion:
    return EmittedVersion(row.borrador_id, _snapshot_from_row(row), bytes(row.pdf))


class PostgresVersionTransaction:
    def __init__(self, db: Session):
        self.db = db
        self.row = None

    def stage(self, quote_id: str, snapshot: VersionSnapshot, pdf: bytes):
        visible = snapshot.visible
        self.row = VersionCotizacion(
            id=snapshot.code, borrador_id=quote_id,
            fecha_emision=datetime.combine(snapshot.issued_at, time.min),
            identidad=snapshot.identity, pdf=pdf,
            total_congelado=visible.total,
            datos_inmutables={
                "visible": {
                    "company": visible.company, "client": visible.client,
                    "service_address": visible.service_address, "scope": visible.scope,
                    "period": visible.period,
                    "groups": [vars(g) for g in visible.groups],
                    "subtotal": str(visible.subtotal), "tax": str(visible.tax),
                    "total": str(visible.total),
                },
                "price_values": {k: str(v) for k, v in snapshot.price_values},
            },
        )
        self.db.add(self.row)

    def commit(self) -> EmittedVersion:
        self.db.commit()
        return _emitted(self.row)

    def rollback(self):
        self.db.rollback()


class PostgresVersionStore:
    def __init__(self, db: Session):
        self.db = db

    def find_by_identity(self, quote_id: str, identity: str):
        row = self.db.query(VersionCotizacion).filter_by(
            borrador_id=quote_id, identidad=identity,
        ).first()
        return _emitted(row) if row else None

    def begin(self):
        return PostgresVersionTransaction(self.db)

    def list_versions(self):
        rows = self.db.query(VersionCotizacion).order_by(VersionCotizacion.fecha_emision.desc()).all()
        return tuple(_emitted(row) for row in rows)

    def get_version(self, quote_id: str, code: str):
        row = self.db.query(VersionCotizacion).filter_by(borrador_id=quote_id, id=code).first()
        return _emitted(row) if row else None
