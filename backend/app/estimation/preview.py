"""Servicio de Vista Previa y validador de emisión conforme al contrato de integración (B07 y B08).

Cubre RF-02, RF-03, RF-04, RF-12, RF-13, RF-18–RF-21, RF-23, RF-32 y RF-33.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal, ROUND_CEILING
from typing import Optional, Sequence, Union

from backend.app.estimation.calendar import (
    PeriodType,
    GroupCalendarInput,
    CalendarSummary,
    calculate_calendar_summary,
    calculate_period_limits,
    normalize_weekday,
)
from backend.app.estimation.effort import (
    InfrastructureState,
    WorkTypeEffortInput,
    GroupEffortResult,
    calculate_group_effort,
    calculate_daily_window_hours,
    check_daily_window_fit,
    to_decimal,
)
from backend.app.estimation.pricing import (
    ResourceKind,
    ResourceScope,
    ResourceInput,
    LaborCostInput,
    PricingSummary,
    calculate_pricing,
)


@dataclass
class ClientDraftInput:
    """Datos del cliente en borrador (RF-01, RF-02)."""
    name: Optional[str] = None
    service_address: Optional[str] = None
    identification: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class ServiceDraftInput:
    """Datos del servicio en borrador (RF-03)."""
    infrastructure_type: Optional[str] = None
    cleaning_type: Optional[str] = None
    start_date: Optional[date] = None
    period_type: Optional[Union[PeriodType, str]] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


@dataclass
class WorkTypeDraftInput:
    """Datos de trabajo general o especializado en borrador (RF-04, RF-12, RF-13)."""
    enabled: bool = False
    productivity_sqm_per_hour: Optional[Union[int, float, str, Decimal]] = None
    hourly_rate_usd: Optional[Union[int, float, str, Decimal]] = None
    assigned_workers: int = 1
    custom_surface_sqm: Optional[Union[int, float, str, Decimal]] = None
    adjusted_hours_per_intervention: Optional[Union[int, float, str, Decimal]] = None


@dataclass
class GroupDraftInput:
    """Datos de un grupo de espacios en borrador (RF-04, RF-05, RF-13)."""
    group_id: str
    name: Optional[str] = None
    units_count: Optional[int] = None
    sqm_per_unit: Optional[Union[int, float, str, Decimal]] = None
    service_days: Optional[Sequence[Union[str, int]]] = None
    visits_per_day: Optional[int] = None
    state: Optional[Union[InfrastructureState, str]] = None
    profile_id: Optional[str] = None
    custom_state_factor: Optional[Union[int, float, str, Decimal]] = None
    zone: Optional[str] = None
    tasks_description: Optional[str] = None
    general_work: Optional[WorkTypeDraftInput] = None
    specialized_work: Optional[WorkTypeDraftInput] = None


@dataclass
class ResourceDraftInput:
    """Datos de un recurso en borrador (RF-20)."""
    resource_id: str
    description: Optional[str] = None
    kind: Optional[Union[ResourceKind, str]] = None
    scope: Optional[Union[ResourceScope, str]] = None
    group_id: Optional[str] = None
    quantity: Optional[Union[int, float, str, Decimal]] = None
    unit_cost_usd: Optional[Union[int, float, str, Decimal]] = None
    unit: str = "unidad"


@dataclass
class QuoteDraftInput:
    """Entrada completa de una cotización en borrador."""
    quote_id: str
    client: Optional[ClientDraftInput] = None
    service: Optional[ServiceDraftInput] = None
    groups: list[GroupDraftInput] = field(default_factory=list)
    resources: list[ResourceDraftInput] = field(default_factory=list)
    margin_percentage: Union[int, float, str, Decimal] = Decimal("0")
    discount_usd: Union[int, float, str, Decimal] = Decimal("0")
    tax_percentage: Union[int, float, str, Decimal] = Decimal("15")


@dataclass
class EstimationPreviewResult:
    """Resultado unificado de vista previa y validación de emisión (B08)."""
    quote_id: str
    is_emission_valid: bool
    pending_emission_issues: list[str]
    can_save_draft: bool = True
    calendar_summary: Optional[CalendarSummary] = None
    group_efforts: dict[str, GroupEffortResult] = field(default_factory=dict)
    pricing_summary: Optional[PricingSummary] = None


def generate_estimation_preview(quote: QuoteDraftInput) -> EstimationPreviewResult:
    """Calcula y valida la vista previa completa de una cotización (RF-02–RF-04, RF-12, RF-13, RF-18–RF-23, RF-32–RF-33).

    - Admite borradores incompletos sin fallar (can_save_draft = True).
    - Identifica detalladamente todos los pendientes que bloquean la generación del PDF.
    - Si los datos son válidos, entrega el desglose exacto de calendario, esfuerzo y precios.
    """
    pendings: list[str] = []

    # 1. Validación de Cliente (RF-02)
    if not quote.client:
        pendings.append("Faltan los datos del cliente (nombre y dirección del servicio requeridos para emitir).")
    else:
        if not quote.client.name or not quote.client.name.strip():
            pendings.append("Falta el nombre del cliente para emitir el PDF.")
        if not quote.client.service_address or not quote.client.service_address.strip():
            pendings.append("Falta la dirección del servicio para emitir el PDF.")

    # 2. Validación de Servicio (RF-03)
    service_valid = False
    window_hours: Optional[Decimal] = None
    if not quote.service:
        pendings.append("Faltan los datos del servicio (fecha, período y horario requeridos para emitir).")
    else:
        if not quote.service.start_date:
            pendings.append("Falta la fecha de inicio del servicio.")
        if not quote.service.period_type:
            pendings.append("Falta definir el período (semanal, quincenal o mensual).")

        if not quote.service.start_time or not quote.service.end_time:
            pendings.append("Falta definir el horario de trabajo (hora de inicio y hora de fin).")
        else:
            try:
                window_hours = calculate_daily_window_hours(quote.service.start_time, quote.service.end_time)
            except ValueError as e:
                pendings.append(f"Horario de trabajo inválido: {e}")

        if (
            quote.service.start_date
            and quote.service.period_type
            and window_hours is not None
        ):
            service_valid = True

    # 3. Validación de Grupos (RF-04, RF-12, RF-13, RF-32)
    if not quote.groups:
        pendings.append("La cotización debe tener al menos un grupo de espacios.")

    valid_groups_for_calendar: list[GroupCalendarInput] = []
    effort_inputs_by_group: dict[str, tuple[GroupDraftInput, WorkTypeEffortInput | None, WorkTypeEffortInput | None]] = {}

    for idx, g in enumerate(quote.groups, start=1):
        g_name = g.name.strip() if g.name else f"Grupo #{idx}"
        has_group_error = False

        if not g.name or not g.name.strip():
            pendings.append(f"El grupo #{idx} no tiene nombre.")
            has_group_error = True

        if g.units_count is None or g.units_count <= 0:
            pendings.append(f"El grupo '{g_name}' debe tener una cantidad positiva de unidades.")
            has_group_error = True

        if g.sqm_per_unit is None:
            pendings.append(f"El grupo '{g_name}' debe tener los m² por unidad.")
            has_group_error = True
        else:
            try:
                sqm_dec = to_decimal(g.sqm_per_unit)
                if sqm_dec <= Decimal("0"):
                    pendings.append(f"El grupo '{g_name}' tiene m² por unidad no positivos ({sqm_dec}).")
                    has_group_error = True
            except ValueError:
                pendings.append(f"El grupo '{g_name}' tiene m² por unidad inválidos.")
                has_group_error = True

        if not g.service_days or len(g.service_days) == 0:
            pendings.append(f"El grupo '{g_name}' debe tener al menos un día de servicio en la semana.")
            has_group_error = True
        else:
            for d in g.service_days:
                try:
                    normalize_weekday(d)
                except ValueError:
                    pendings.append(f"El grupo '{g_name}' tiene un día de servicio inválido: '{d}'.")
                    has_group_error = True

        if g.visits_per_day is None or g.visits_per_day <= 0:
            pendings.append(f"El grupo '{g_name}' debe tener visitas por día mayores a cero.")
            has_group_error = True

        if not g.state:
            pendings.append(f"El grupo '{g_name}' debe indicar su estado (bueno, regular o malo).")
            has_group_error = True

        if not g.profile_id or not g.profile_id.strip():
            pendings.append(f"El grupo '{g_name}' debe tener un perfil de referencia asignado.")
            has_group_error = True

        # Tipos de trabajo
        gen_in: Optional[WorkTypeEffortInput] = None
        spec_in: Optional[WorkTypeEffortInput] = None
        has_work_active = False

        if g.general_work and g.general_work.enabled:
            has_work_active = True
            if (
                g.general_work.productivity_sqm_per_hour is None
                or to_decimal(g.general_work.productivity_sqm_per_hour) <= Decimal("0")
            ):
                pendings.append(f"El grupo '{g_name}' tiene trabajo general activo pero falta un rendimiento positivo en m²/h.")
                has_group_error = True
            elif (
                g.general_work.hourly_rate_usd is None
                or to_decimal(g.general_work.hourly_rate_usd) <= Decimal("0")
            ):
                pendings.append(f"El grupo '{g_name}' tiene trabajo general activo pero falta una tarifa horaria positiva.")
                has_group_error = True
            else:
                gen_in = WorkTypeEffortInput(
                    enabled=True,
                    productivity_sqm_per_hour=to_decimal(g.general_work.productivity_sqm_per_hour),
                    hourly_rate_usd=to_decimal(g.general_work.hourly_rate_usd),
                    assigned_workers=g.general_work.assigned_workers,
                    adjusted_hours_per_intervention=(
                        to_decimal(g.general_work.adjusted_hours_per_intervention)
                        if g.general_work.adjusted_hours_per_intervention is not None
                        else None
                    ),
                )

        if g.specialized_work and g.specialized_work.enabled:
            has_work_active = True
            if (
                g.specialized_work.custom_surface_sqm is None
                or to_decimal(g.specialized_work.custom_surface_sqm) <= Decimal("0")
            ):
                pendings.append(f"El grupo '{g_name}' tiene trabajo especializado pero falta confirmar su superficie propia en m².")
                has_group_error = True
            elif (
                g.specialized_work.productivity_sqm_per_hour is None
                or to_decimal(g.specialized_work.productivity_sqm_per_hour) <= Decimal("0")
            ):
                pendings.append(f"El grupo '{g_name}' tiene trabajo especializado pero falta un rendimiento positivo.")
                has_group_error = True
            elif (
                g.specialized_work.hourly_rate_usd is None
                or to_decimal(g.specialized_work.hourly_rate_usd) <= Decimal("0")
            ):
                pendings.append(f"El grupo '{g_name}' tiene trabajo especializado pero falta una tarifa horaria positiva.")
                has_group_error = True
            else:
                spec_in = WorkTypeEffortInput(
                    enabled=True,
                    productivity_sqm_per_hour=to_decimal(g.specialized_work.productivity_sqm_per_hour),
                    hourly_rate_usd=to_decimal(g.specialized_work.hourly_rate_usd),
                    assigned_workers=g.specialized_work.assigned_workers,
                    custom_surface_sqm=to_decimal(g.specialized_work.custom_surface_sqm),
                    adjusted_hours_per_intervention=(
                        to_decimal(g.specialized_work.adjusted_hours_per_intervention)
                        if g.specialized_work.adjusted_hours_per_intervention is not None
                        else None
                    ),
                )

        if not has_work_active:
            pendings.append(f"El grupo '{g_name}' debe tener al menos un tipo de trabajo activo (general, especializado o ambos).")
            has_group_error = True

        if not has_group_error and g.service_days and g.visits_per_day:
            valid_groups_for_calendar.append(
                GroupCalendarInput(
                    group_id=g.group_id,
                    service_days=g.service_days,
                    visits_per_day=g.visits_per_day,
                )
            )
            effort_inputs_by_group[g.group_id] = (g, gen_in, spec_in)

    # 4. Cálculo de Calendario si el servicio y al menos un grupo son válidos
    cal_summary: Optional[CalendarSummary] = None
    if service_valid and valid_groups_for_calendar and quote.service and quote.service.start_date and quote.service.period_type:
        try:
            cal_summary = calculate_calendar_summary(
                start_date=quote.service.start_date,
                period_type=quote.service.period_type,
                groups=valid_groups_for_calendar,
            )
        except Exception as e:
            pendings.append(f"Error al calcular calendario: {e}")

    # 5. Cálculo de Esfuerzos y Comprobación de Ventana Diaria (RF-23)
    group_efforts: dict[str, GroupEffortResult] = {}
    labor_cost_inputs: list[LaborCostInput] = []

    for gid, (g_draft, gen_in, spec_in) in effort_inputs_by_group.items():
        try:
            effort_res = calculate_group_effort(
                group_id=gid,
                units_count=g_draft.units_count or 1,
                sqm_per_unit=g_draft.sqm_per_unit or Decimal("1"),
                state=g_draft.state or InfrastructureState.BUENO,
                general_config=gen_in,
                specialized_config=spec_in,
                custom_state_factor=g_draft.custom_state_factor,
            )
            group_efforts[gid] = effort_res

            # Comprobar si cabe en la ventana horaria si horario está disponible
            if window_hours is not None and quote.service and quote.service.start_time and quote.service.end_time:
                # RF-19: each independent team must fit all daily visits. The
                # suggestion never changes the chosen staff, hours or price.
                for work in (effort_res.general, effort_res.specialized):
                    if work is not None:
                        required = work.total_hours_per_intervention * Decimal(g_draft.visits_per_day or 1) / window_hours
                        work.suggested_workers = max(1, int(required.to_integral_value(rounding=ROUND_CEILING)))
                fits, daily_dur, win = check_daily_window_fit(
                    visit_duration_hours=effort_res.visit_duration_hours,
                    visits_per_day=g_draft.visits_per_day or 1,
                    start_time=quote.service.start_time,
                    end_time=quote.service.end_time,
                )
                if not fits:
                    g_lbl = g_draft.name or gid
                    pendings.append(
                        f"En el grupo '{g_lbl}', la suma de las duraciones estimadas de sus visitas ({daily_dur:.2f} h) "
                        f"excede la ventana de trabajo disponible ({win:.2f} h)."
                    )

            # Preparar insumos de mano de obra para pricing si hay calendario
            if cal_summary:
                interventions = cal_summary.group_interventions.get(gid, 0)
                if effort_res.general:
                    labor_cost_inputs.append(
                        LaborCostInput(
                            group_id=gid,
                            group_name=g_draft.name or gid,
                            work_type="general",
                            hours_per_intervention=effort_res.general.total_hours_per_intervention,
                            interventions_count=interventions,
                            hourly_rate_usd=effort_res.general.hourly_rate_usd,
                        )
                    )
                if effort_res.specialized:
                    labor_cost_inputs.append(
                        LaborCostInput(
                            group_id=gid,
                            group_name=g_draft.name or gid,
                            work_type="especializado",
                            hours_per_intervention=effort_res.specialized.total_hours_per_intervention,
                            interventions_count=interventions,
                            hourly_rate_usd=effort_res.specialized.hourly_rate_usd,
                        )
                    )

        except Exception as e:
            pendings.append(f"Error al calcular esfuerzo del grupo '{g_draft.name or gid}': {e}")

    # 6. Validación y cálculo de Recursos (RF-20, RF-32)
    valid_resources: list[ResourceInput] = []
    group_ids_set = {g.group_id for g in quote.groups}

    for r_idx, r in enumerate(quote.resources, start=1):
        r_name = r.description or f"Recurso #{r_idx}"
        if not r.description or not r.description.strip():
            pendings.append(f"El recurso #{r_idx} no tiene descripción.")
        if r.quantity is None or to_decimal(r.quantity) <= Decimal("0"):
            pendings.append(f"El recurso '{r_name}' debe tener una cantidad decimal positiva (> 0).")
        if r.unit_cost_usd is None or to_decimal(r.unit_cost_usd) < Decimal("0"):
            pendings.append(f"El recurso '{r_name}' debe tener un costo unitario no negativo (>= 0).")
        if r.scope == ResourceScope.GRUPO or str(r.scope).lower() == "grupo":
            if not r.group_id or r.group_id not in group_ids_set:
                pendings.append(f"El recurso '{r_name}' tiene ámbito de grupo pero su group_id no corresponde a ningún grupo de la cotización.")
        try:
            if r.description and r.quantity is not None and r.unit_cost_usd is not None:
                valid_resources.append(
                    ResourceInput(
                        resource_id=r.resource_id,
                        description=r.description,
                        kind=r.kind or ResourceKind.INSUMO,
                        scope=r.scope or ResourceScope.COMPARTIDO,
                        quantity=to_decimal(r.quantity),
                        unit_cost_usd=to_decimal(r.unit_cost_usd),
                        unit=r.unit or "unidad",
                        group_id=r.group_id,
                    )
                )
        except Exception as e:
            pendings.append(f"Recurso '{r_name}' inválido: {e}")

    # 7. Cálculo financiero (Pricing) si se pudo estructurar
    pricing_res: Optional[PricingSummary] = None
    if cal_summary and (labor_cost_inputs or valid_resources):
        try:
            pricing_res = calculate_pricing(
                labor_inputs=labor_cost_inputs,
                resource_inputs=valid_resources,
                group_interventions=cal_summary.group_interventions,
                shared_service_days_count=cal_summary.shared_service_days_count,
                margin_percentage=quote.margin_percentage,
                discount_usd=quote.discount_usd,
                tax_percentage=quote.tax_percentage,
            )
            if not pricing_res.is_subtotal_valid and pricing_res.subtotal_error:
                pendings.append(pricing_res.subtotal_error)
        except Exception as e:
            pendings.append(f"Error al calcular precio: {e}")

    # Decisión final de emisión
    is_emission_valid = len(pendings) == 0 and pricing_res is not None and pricing_res.is_subtotal_valid

    return EstimationPreviewResult(
        quote_id=quote.quote_id,
        is_emission_valid=is_emission_valid,
        pending_emission_issues=pendings,
        can_save_draft=True,
        calendar_summary=cal_summary,
        group_efforts=group_efforts,
        pricing_summary=pricing_res,
    )
