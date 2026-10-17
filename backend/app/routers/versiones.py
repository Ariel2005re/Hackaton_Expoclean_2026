"""Issue, search and download immutable quotation versions."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.documents.composition import GroupSchedule, QuotePdfSnapshot
from backend.app.documents.history import HistoryService
from backend.app.documents.identity import VersionSnapshot
from backend.app.documents.issuance import EmissionService
from backend.app.estimation.effort import DEFAULT_STATE_FACTORS, InfrastructureState
from backend.app.estimation.preview import generate_estimation_preview
from backend.app.integration import draft_to_estimation, resolved_calculation_data
from backend.app.models.cotizacion import CotizacionBorrador
from backend.app.models.config import EmpresaConfig
from backend.app.version_store import PostgresVersionStore

router = APIRouter(tags=["Versiones PDF"])


def _price_values(quote, result):
    values = {
        "margin_percentage": Decimal(str(quote.margin_percentage)),
        "discount_usd": Decimal(str(quote.discount_usd)),
        "tax_percentage": Decimal(str(quote.tax_percentage)),
    }
    for i, group in enumerate(quote.groups):
        prefix = f"group_{i}"
        for key in ("units_count", "sqm_per_unit", "visits_per_day"):
            values[f"{prefix}_{key}"] = Decimal(str(getattr(group, key)))
        factor = group.custom_state_factor
        if factor is None:
            factor = DEFAULT_STATE_FACTORS[InfrastructureState(group.state)]
        values[f"{prefix}_state_factor"] = Decimal(str(factor))
        for kind, work in (("general", group.general_work), ("specialized", group.specialized_work)):
            if not work or not work.enabled:
                continue
            for key in ("productivity_sqm_per_hour", "hourly_rate_usd",
                        "custom_surface_sqm", "adjusted_hours_per_intervention"):
                value = getattr(work, key)
                if value is not None:
                    values[f"{prefix}_{kind}_{key}"] = Decimal(str(value))
    for i, resource in enumerate(quote.resources):
        values[f"resource_{i}_quantity"] = Decimal(str(resource.quantity))
        values[f"resource_{i}_unit_cost"] = Decimal(str(resource.unit_cost_usd))
    for i, line in enumerate(result.pricing_summary.labor_lines):
        values[f"labor_line_{i}"] = line.rounded_total
    for i, line in enumerate(result.pricing_summary.group_resource_lines + result.pricing_summary.shared_resource_lines):
        values[f"resource_line_{i}"] = line.rounded_total
    return values


def _snapshot(data, company_name="Empresa de limpieza"):
    quote = draft_to_estimation(data)
    result = generate_estimation_preview(quote)
    if not result.is_emission_valid:
        raise HTTPException(status_code=422, detail=result.pending_emission_issues)
    calendar = result.calendar_summary
    price = result.pricing_summary
    service = quote.service
    groups = tuple(
        GroupSchedule(
            spaces=f"{g.units_count} × {g.name} ({result.group_efforts[g.group_id].physical_sqm} m²)"
                   + (f"; zona: {g.zone}" if g.zone else "")
                   + (f"; tareas: {g.tasks_description}" if g.tasks_description else ""),
            days=", ".join(str(day) for day in g.service_days),
            visits_per_day=g.visits_per_day,
            hours=f"{service.start_time.strftime('%H:%M')}–{service.end_time.strftime('%H:%M')}",
        ) for g in quote.groups
    )
    scope = ", ".join(filter(None, (service.infrastructure_type, service.cleaning_type))) or "Servicio de limpieza"
    pdf_data = QuotePdfSnapshot(
        company=company_name, client=quote.client.name,
        service_address=quote.client.service_address, scope=scope,
        period=f"{calendar.period_type.value}: {calendar.start_date.isoformat()} a {calendar.end_date.isoformat()}",
        groups=groups, subtotal=price.subtotal_usd,
        tax=price.tax_usd, total=price.total_usd,
    )
    return VersionSnapshot.from_quote_pdf(
        pdf_data, _price_values(quote, result),
        code=f"COT-{uuid4().hex[:12].upper()}",
        issued_at=datetime.now(ZoneInfo("America/Guayaquil")).date(),
    )


@router.post("/cotizaciones/{quote_id}/versiones")
def issue(quote_id: str, db: Session = Depends(get_db)):
    draft = db.get(CotizacionBorrador, quote_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    try:
        company = db.query(EmpresaConfig).first()
        snapshot = _snapshot(resolved_calculation_data(draft.datos, db),
                             company.nombre if company else "Empresa de limpieza")
        version = EmissionService(PostgresVersionStore(db)).emit(snapshot, quote_id=quote_id)
    except HTTPException:
        raise
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "quote_id": quote_id, "code": version.snapshot.code,
        "issued_at": version.snapshot.issued_at.isoformat(),
        "total_usd": str(version.snapshot.visible.total),
        "pdf_url": f"/cotizaciones/{quote_id}/versiones/{version.snapshot.code}/pdf",
    }


@router.get("/historial")
def history(query: str = "", db: Session = Depends(get_db)):
    entries = HistoryService(PostgresVersionStore(db)).search(query)
    return [{**vars(entry), "issued_at": entry.issued_at.isoformat(),
             "total": str(entry.total)} for entry in entries]


@router.get("/cotizaciones/{quote_id}/versiones/{code}/pdf")
def download(quote_id: str, code: str, db: Session = Depends(get_db)):
    try:
        pdf = HistoryService(PostgresVersionStore(db)).download(quote_id, code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{code}.pdf"'})
