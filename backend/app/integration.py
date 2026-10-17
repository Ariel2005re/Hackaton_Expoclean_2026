"""Adapters between the persisted draft contract and the estimation engine."""

from dataclasses import asdict, fields
from datetime import date, time
from decimal import Decimal
from copy import deepcopy

from fastapi.encoders import jsonable_encoder

from backend.app.estimation.preview import (
    ClientDraftInput, ServiceDraftInput, WorkTypeDraftInput, GroupDraftInput,
    ResourceDraftInput, QuoteDraftInput, generate_estimation_preview,
)


def _work(value):
    if not isinstance(value, dict):
        return None
    names = {f.name for f in fields(WorkTypeDraftInput)}
    return WorkTypeDraftInput(**{k: v for k, v in value.items() if k in names})


def resolved_calculation_data(data: dict, db) -> dict:
    """Apply current editable company assumptions without changing the saved draft."""
    from backend.app.models.config import Factor, PerfilRendimiento, Tarifa, EmpresaConfig
    from backend.app.models.cotizacion import Cliente

    resolved = deepcopy(data)
    if resolved.get("cliente_id"):
        client = db.get(Cliente, resolved["cliente_id"])
        if client:
            resolved["client"] = {**(resolved.get("client") or {})}
            if not resolved["client"].get("name"):
                resolved["client"]["name"] = client.nombre
    company = db.query(EmpresaConfig).first()
    if resolved.get("margin_percentage") is None:
        resolved["margin_percentage"] = company.margen_porcentaje if company else 0
    if resolved.get("tax_percentage") is None:
        resolved["tax_percentage"] = company.impuesto_porcentaje if company else 0
    factors = {row.nombre: row.valor for row in db.query(Factor).all()}
    rates = {row.descripcion: row.monto for row in db.query(Tarifa).all()}
    for group in resolved.get("groups") or []:
        if group.get("custom_state_factor") is None:
            group["custom_state_factor"] = factors.get(group.get("state"))
        profile = None
        try:
            if group.get("profile_id") is not None:
                profile = db.get(PerfilRendimiento, int(group["profile_id"]))
        except (ValueError, TypeError):
            pass
        if profile is None:
            group["profile_id"] = None
        for kind, label in (("general_work", "Personal general"),
                            ("specialized_work", "Personal especializado")):
            work = group.get(kind)
            if not isinstance(work, dict) or not work.get("enabled"):
                continue
            if work.get("productivity_sqm_per_hour") is None and profile:
                work["productivity_sqm_per_hour"] = profile.m2_por_hora
            if work.get("hourly_rate_usd") is None:
                work["hourly_rate_usd"] = rates.get(label)
    return resolved


def draft_to_estimation(data: dict) -> QuoteDraftInput:
    client_data = data.get("client") or {}
    service_data = data.get("service") or {}
    start_date = service_data.get("start_date")
    start_time = service_data.get("start_time")
    end_time = service_data.get("end_time")
    service_data = {**service_data}
    if isinstance(start_date, str) and start_date:
        try:
            service_data["start_date"] = date.fromisoformat(start_date)
        except ValueError:
            service_data["start_date"] = None
    for key, value in (("start_time", start_time), ("end_time", end_time)):
        if isinstance(value, str) and value:
            try:
                service_data[key] = time.fromisoformat(value)
            except ValueError:
                service_data[key] = None
    groups = []
    for item in data.get("groups") or []:
        group = {**item}
        group["general_work"] = _work(group.get("general_work"))
        group["specialized_work"] = _work(group.get("specialized_work"))
        names = {f.name for f in fields(GroupDraftInput)}
        groups.append(GroupDraftInput(**{k: v for k, v in group.items() if k in names}))
    resources = [ResourceDraftInput(**item) for item in data.get("resources") or []]
    return QuoteDraftInput(
        quote_id=data["id"],
        client=ClientDraftInput(**client_data) if client_data else None,
        service=ServiceDraftInput(**service_data) if service_data else None,
        groups=groups,
        resources=resources,
        margin_percentage=data.get("margin_percentage") if data.get("margin_percentage") is not None else "0",
        discount_usd=data.get("discount_usd", "0"),
        tax_percentage=data.get("tax_percentage") if data.get("tax_percentage") is not None else "0",
    )


def preview_for_draft(data: dict) -> dict:
    try:
        result = generate_estimation_preview(draft_to_estimation(data))
        return jsonable_encoder(asdict(result))
    except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
        return {"quote_id": data.get("id"), "is_emission_valid": False,
                "can_save_draft": True, "pending_emission_issues": [str(exc)],
                "calendar_summary": None, "group_efforts": {}, "pricing_summary": None}


def decimal_text(value) -> str:
    return str(Decimal(str(value)))
