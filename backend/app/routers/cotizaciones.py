"""Editable quote drafts and persisted estimation previews (RF-01–RF-23, RF-32–RF-33)."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.integration import preview_for_draft, resolved_calculation_data
from backend.app.models.cotizacion import CotizacionBorrador

router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones"])


class DraftPayload(BaseModel):
    id: str | None = None
    cliente_id: int | None = None
    client: dict | None = None
    service: dict | None = None
    groups: list[dict] = Field(default_factory=list)
    resources: list[dict] = Field(default_factory=list)
    margin_percentage: str | int | float | None = None
    discount_usd: str | int | float = "0"
    tax_percentage: str | int | float | None = None


def _get_draft(db: Session, quote_id: str) -> CotizacionBorrador:
    draft = db.get(CotizacionBorrador, quote_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    return draft


@router.post("/", status_code=201)
def create_draft(payload: DraftPayload, db: Session = Depends(get_db)):
    data = payload.model_dump(mode="json")
    data["id"] = data.get("id") or str(uuid4())
    if db.get(CotizacionBorrador, data["id"]):
        raise HTTPException(status_code=409, detail="Ya existe una cotización con ese id")
    draft = CotizacionBorrador(
        id=data["id"], cliente_id=data.get("cliente_id"),
        periodo=(data.get("service") or {}).get("period_type"), datos=data,
    )
    db.add(draft)
    db.commit()
    return data


@router.put("/{quote_id}")
def update_draft(quote_id: str, payload: DraftPayload, db: Session = Depends(get_db)):
    draft = _get_draft(db, quote_id)
    if payload.id and payload.id != quote_id:
        raise HTTPException(status_code=400, detail="El id del borrador no puede cambiar")
    data = payload.model_dump(mode="json")
    data["id"] = quote_id
    draft.datos = data
    draft.cliente_id = data.get("cliente_id")
    draft.periodo = (data.get("service") or {}).get("period_type")
    db.commit()
    return data


@router.get("/")
def list_drafts(db: Session = Depends(get_db)):
    """Recover editable quotes independently of browser storage (RF-22, RF-28)."""
    return [row.datos for row in db.query(CotizacionBorrador).order_by(CotizacionBorrador.id).all()]


@router.get("/{quote_id}")
def get_draft(quote_id: str, db: Session = Depends(get_db)):
    return _get_draft(db, quote_id).datos


@router.get("/{quote_id}/preview")
def get_preview(quote_id: str, db: Session = Depends(get_db)):
    return preview_for_draft(resolved_calculation_data(_get_draft(db, quote_id).datos, db))
