"""Persisted extraction review attached to a quote draft (RF-06–RF-11, RF-29–RF-31)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.models.cotizacion import CotizacionBorrador
from backend.app.models.ia_versiones import PropuestaIA
from backend.app.extraction.models import AnalyzeSpacesPayload, ExtractionInputRequest, ReviewSessionState
from backend.app.extraction.proposal_manager import ProposalReviewSession
from backend.app.extraction.service import ExtractionService

router = APIRouter(prefix="/cotizaciones/{quote_id}/propuestas", tags=["Propuestas IA"])


def get_service() -> ExtractionService:
    return ExtractionService()


def _draft(db, quote_id):
    draft = db.get(CotizacionBorrador, quote_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    return draft


def _proposal(db, quote_id, proposal_id):
    row = db.get(PropuestaIA, proposal_id)
    if row is None or row.cotizacion_id != quote_id:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    return row


@router.post("/analizar")
def analyze(quote_id: str, payload: AnalyzeSpacesPayload, db: Session = Depends(get_db),
            service: ExtractionService = Depends(get_service)):
    _draft(db, quote_id)
    request = ExtractionInputRequest(
        text=payload.text, confirmed=payload.confirmed,
        personal_data_warning_acknowledged=payload.personal_data_warning_acknowledged,
    )
    result = service.analyze_description(request)
    state = ReviewSessionState(
        original_text=result.original_text, revisable_groups=result.revisable_groups,
        defective_groups=result.defective_groups,
    )
    row = PropuestaIA(
        cotizacion_id=quote_id, texto_original=payload.text,
        estado="revisable", datos_extraidos=result.model_dump(mode="json"),
        estado_revision=state.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "analysis": row.datos_extraidos, "review": row.estado_revision}


@router.get("/{proposal_id}")
def get_proposal(quote_id: str, proposal_id: int, db: Session = Depends(get_db)):
    row = _proposal(db, quote_id, proposal_id)
    return {"id": row.id, "analysis": row.datos_extraidos, "review": row.estado_revision}


class ReviewAction(BaseModel):
    group_id: str | None = None
    group_id_1: str | None = None
    group_id_2: str | None = None
    merged_name: str | None = None
    attribute_name: str | None = None
    new_value: object | None = None
    human_note: str | None = None
    split_quantities: tuple[int, int] | None = None
    split_names: tuple[str, str] | None = None


@router.post("/{proposal_id}/{action}")
def review_action(quote_id: str, proposal_id: int, action: str, payload: ReviewAction,
                  db: Session = Depends(get_db)):
    draft = _draft(db, quote_id)
    row = _proposal(db, quote_id, proposal_id)
    state = ReviewSessionState.model_validate(row.estado_revision)
    session = ProposalReviewSession(
        original_text=state.original_text, revisable_groups=state.revisable_groups,
        defective_groups=state.defective_groups, confirmed_groups=state.confirmed_groups,
    )
    session.discarded_groups = state.discarded_groups
    try:
        if action == "corregir":
            session.correct_attribute(payload.group_id, payload.attribute_name,
                                      payload.new_value, payload.human_note)
        elif action == "combinar":
            session.merge_groups(payload.group_id_1, payload.group_id_2, payload.merged_name)
        elif action == "separar":
            session.split_group(payload.group_id, payload.split_quantities, payload.split_names)
        elif action == "descartar":
            session.discard_group(payload.group_id)
        elif action == "confirmar":
            group = session.confirm_group(payload.group_id)
            data = {**draft.datos}
            groups = list(data.get("groups") or [])
            if not any(g.get("group_id") == group.id for g in groups):
                groups.append({
                    "group_id": group.id, "name": group.name,
                    "units_count": group.quantity, "sqm_per_unit": group.unit_area_m2,
                    "service_days": group.service_days,
                    "visits_per_day": group.visits_per_day, "state": group.condition,
                    "profile_id": None,
                    "general_work": {"enabled": group.cleaning_type in ("general", "ambos")},
                    "specialized_work": {"enabled": group.cleaning_type in ("especializado", "ambos")},
                    "provenance": {k: v.model_dump(mode="json") for k, v in group.attributes.items()},
                })
                data["groups"] = groups
                draft.datos = data
        else:
            raise HTTPException(status_code=404, detail="Operación desconocida")
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row.estado_revision = ReviewSessionState(
        original_text=session.original_text, revisable_groups=session.revisable_groups,
        defective_groups=session.defective_groups, confirmed_groups=session.confirmed_groups,
        discarded_groups=session.discarded_groups,
    ).model_dump(mode="json")
    db.commit()
    return {"review": row.estado_revision, "draft": draft.datos}
