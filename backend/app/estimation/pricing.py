"""Motor de costeo, desglose de recursos, precios y redondeo centavo a centavo.

Cumple con RF-18, RF-20, RF-21, RF-32 y RF-33 de specs/001-hackaton/spec.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Sequence, Union

from backend.app.estimation.effort import to_decimal


class ResourceKind(str, Enum):
    """Tipo de recurso según RF-20 y RF-21."""
    INSUMO = "insumo"
    HERRAMIENTA = "herramienta"


class ResourceScope(str, Enum):
    """Ámbito del recurso según RF-20."""
    GRUPO = "grupo"              # Se cobra por intervención del grupo
    COMPARTIDO = "compartido"    # Se cobra por jornada con servicio


def round_half_up(value: Decimal) -> Decimal:
    """Aplica la regla de redondeo al centavo mitad hacia arriba (RF-32)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class ResourceInput:
    """Definición de un recurso de grupo o compartido para cotización (RF-20, RF-32)."""
    resource_id: str
    description: str
    kind: Union[ResourceKind, str]
    scope: Union[ResourceScope, str]
    quantity: Union[int, float, str, Decimal]  # Positivo > 0
    unit_cost_usd: Union[int, float, str, Decimal]  # No negativo >= 0
    unit: str = "unidad"
    group_id: Optional[str] = None  # Obligatorio si scope == GRUPO

    def __post_init__(self):
        if not self.resource_id:
            raise ValueError("resource_id es obligatorio")
        if not self.description:
            raise ValueError("description es obligatoria")

        self.kind = ResourceKind(self.kind.lower().strip()) if isinstance(self.kind, str) else self.kind
        self.scope = ResourceScope(self.scope.lower().strip()) if isinstance(self.scope, str) else self.scope

        self.quantity = to_decimal(self.quantity, "cantidad de recurso")
        self.unit_cost_usd = to_decimal(self.unit_cost_usd, "costo unitario de recurso")

        if self.quantity <= Decimal("0"):
            raise ValueError(f"La cantidad de recurso debe ser positiva (> 0). Recibido: {self.quantity}")
        if self.unit_cost_usd < Decimal("0"):
            raise ValueError(f"El costo unitario de recurso no puede ser negativo (>= 0). Recibido: {self.unit_cost_usd}")

        if self.scope == ResourceScope.GRUPO and not self.group_id:
            raise ValueError("Un recurso con ámbito 'grupo' debe especificar group_id.")


@dataclass
class CostLine:
    """Línea de costo individual acumulada para el período (RF-21, RF-32)."""
    category: str  # 'mano_de_obra_general', 'mano_de_obra_especializada', 'insumo', 'herramienta'
    description: str
    scope: str     # 'grupo' o 'compartido'
    group_id: Optional[str]
    recurrence_count: int  # Intervenciones o jornadas
    quantity_per_recurrence: Decimal
    unit_cost: Decimal
    raw_total: Decimal
    rounded_total: Decimal


@dataclass
class LaborCostInput:
    """Datos para calcular el costo laboral de un grupo y tipo de trabajo en el período."""
    group_id: str
    group_name: str
    work_type: str  # 'general' o 'especializado'
    hours_per_intervention: Union[int, float, str, Decimal]
    interventions_count: int
    hourly_rate_usd: Union[int, float, str, Decimal]

    def __post_init__(self):
        self.hours_per_intervention = to_decimal(self.hours_per_intervention, "horas por intervención")
        self.hourly_rate_usd = to_decimal(self.hourly_rate_usd, "tarifa horaria")

        if self.interventions_count < 0:
            raise ValueError(f"interventions_count no puede ser negativo. Recibido: {self.interventions_count}")
        if self.hours_per_intervention <= Decimal("0"):
            raise ValueError(f"Las horas de trabajo deben ser positivas (> 0). Recibido: {self.hours_per_intervention}")
        if self.hourly_rate_usd <= Decimal("0"):
            raise ValueError(f"La tarifa horaria debe ser positiva (> 0). Recibido: {self.hourly_rate_usd}")


@dataclass
class PricingSummary:
    """Desglose financiero completo del período conforme a RF-21 y RF-32."""
    labor_lines: list[CostLine]
    group_resource_lines: list[CostLine]
    shared_resource_lines: list[CostLine]

    total_labor_general_usd: Decimal
    total_labor_specialized_usd: Decimal
    total_insumos_usd: Decimal
    total_herramientas_usd: Decimal

    direct_cost_usd: Decimal
    margin_percentage: Decimal
    margin_usd: Decimal
    discount_usd: Decimal
    subtotal_usd: Decimal
    tax_percentage: Decimal
    tax_usd: Decimal
    total_usd: Decimal

    is_subtotal_valid: bool
    subtotal_error: Optional[str] = None


def calculate_pricing(
    labor_inputs: Sequence[LaborCostInput],
    resource_inputs: Sequence[ResourceInput],
    group_interventions: dict[str, int],
    shared_service_days_count: int,
    margin_percentage: Union[int, float, str, Decimal] = Decimal("0"),
    discount_usd: Union[int, float, str, Decimal] = Decimal("0"),
    tax_percentage: Union[int, float, str, Decimal] = Decimal("15"),  # Ejemplo habitual IVA 15%
) -> PricingSummary:
    """Calcula el desglose económico exacto del período con redondeo por línea (RF-21, RF-32).

    1. Cada línea laboral se calcula como: horas_acumuladas * tarifa_usd y se redondea a centavos.
    2. Cada recurso de grupo se calcula como: cantidad * costo_unitario * intervenciones_grupo y se redondea a centavos.
    3. Cada recurso compartido se calcula como: cantidad * costo_unitario * jornadas_compartidas y se redondea a centavos.
    4. Costo directo = suma de todas las líneas redondeadas.
    5. Margen USD = round_half_up(Costo directo * (margen_pct / 100)).
    6. Descuento USD = round_half_up(descuento_usd).
    7. Subtotal = Costo directo + Margen USD - Descuento USD.
       Si Subtotal <= 0, señala la causa e impide el PDF.
    8. Impuesto USD = round_half_up(Subtotal * (tax_pct / 100)).
    9. Total USD = Subtotal + Impuesto USD.
    """
    dec_margin_pct = to_decimal(margin_percentage, "margen porcentual")
    dec_discount = to_decimal(discount_usd, "descuento fijo")
    dec_tax_pct = to_decimal(tax_percentage, "impuesto porcentual")

    if dec_margin_pct < Decimal("0"):
        raise ValueError(f"El porcentaje de margen no puede ser negativo. Recibido: {dec_margin_pct}")
    if dec_discount < Decimal("0"):
        raise ValueError(f"El descuento no puede ser negativo. Recibido: {dec_discount}")
    if dec_tax_pct < Decimal("0"):
        raise ValueError(f"El porcentaje de impuesto no puede ser negativo. Recibido: {dec_tax_pct}")

    # 1. Líneas de mano de obra
    labor_lines: list[CostLine] = []
    tot_labor_gen = Decimal("0.00")
    tot_labor_spec = Decimal("0.00")

    for l_in in labor_inputs:
        accumulated_hours = l_in.hours_per_intervention * Decimal(l_in.interventions_count)
        raw_val = accumulated_hours * l_in.hourly_rate_usd
        rounded_val = round_half_up(raw_val)

        category = f"mano_de_obra_{l_in.work_type.lower()}"
        line = CostLine(
            category=category,
            description=f"Mano de obra {l_in.work_type} - {l_in.group_name}",
            scope="grupo",
            group_id=l_in.group_id,
            recurrence_count=l_in.interventions_count,
            quantity_per_recurrence=l_in.hours_per_intervention,
            unit_cost=l_in.hourly_rate_usd,
            raw_total=raw_val,
            rounded_total=rounded_val,
        )
        labor_lines.append(line)

        if "general" in l_in.work_type.lower():
            tot_labor_gen += rounded_val
        else:
            tot_labor_spec += rounded_val

    # 2. Líneas de recursos
    group_resource_lines: list[CostLine] = []
    shared_resource_lines: list[CostLine] = []
    tot_insumos = Decimal("0.00")
    tot_herramientas = Decimal("0.00")

    for r_in in resource_inputs:
        if r_in.scope == ResourceScope.GRUPO:
            interventions = group_interventions.get(r_in.group_id or "", 0)
            raw_val = r_in.quantity * r_in.unit_cost_usd * Decimal(interventions)
            rounded_val = round_half_up(raw_val)
            line = CostLine(
                category=r_in.kind.value,
                description=f"{r_in.description} (Grupo {r_in.group_id})",
                scope="grupo",
                group_id=r_in.group_id,
                recurrence_count=interventions,
                quantity_per_recurrence=r_in.quantity,
                unit_cost=r_in.unit_cost_usd,
                raw_total=raw_val,
                rounded_total=rounded_val,
            )
            group_resource_lines.append(line)
        else:
            # Ámbito compartido: una vez por cada jornada con servicio
            raw_val = r_in.quantity * r_in.unit_cost_usd * Decimal(shared_service_days_count)
            rounded_val = round_half_up(raw_val)
            line = CostLine(
                category=r_in.kind.value,
                description=f"{r_in.description} (Recurso compartido)",
                scope="compartido",
                group_id=None,
                recurrence_count=shared_service_days_count,
                quantity_per_recurrence=r_in.quantity,
                unit_cost=r_in.unit_cost_usd,
                raw_total=raw_val,
                rounded_total=rounded_val,
            )
            shared_resource_lines.append(line)

        if r_in.kind == ResourceKind.INSUMO:
            tot_insumos += rounded_val
        else:
            tot_herramientas += rounded_val

    # 3. Costo Directo: suma de líneas redondeadas (RF-21)
    direct_cost_usd = (
        tot_labor_gen
        + tot_labor_spec
        + tot_insumos
        + tot_herramientas
    )

    # 4. Margen sobre costo directo y redondeo
    raw_margin = direct_cost_usd * (dec_margin_pct / Decimal("100"))
    margin_usd = round_half_up(raw_margin)

    # 5. Descuento fijo redondeado
    rounded_discount_usd = round_half_up(dec_discount)

    # 6. Subtotal
    subtotal_usd = direct_cost_usd + margin_usd - rounded_discount_usd

    is_subtotal_valid = subtotal_usd > Decimal("0")
    subtotal_error = None
    if not is_subtotal_valid:
        subtotal_error = (
            f"El subtotal de la cotización debe ser positivo (> 0). Valor actual: ${subtotal_usd}. "
            f"El descuento (${rounded_discount_usd}) no puede igualar o superar el costo directo más margen."
        )

    # 7. Impuesto sobre subtotal
    if is_subtotal_valid:
        raw_tax = subtotal_usd * (dec_tax_pct / Decimal("100"))
        tax_usd = round_half_up(raw_tax)
    else:
        tax_usd = Decimal("0.00")

    # 8. Total
    total_usd = subtotal_usd + tax_usd

    return PricingSummary(
        labor_lines=labor_lines,
        group_resource_lines=group_resource_lines,
        shared_resource_lines=shared_resource_lines,
        total_labor_general_usd=tot_labor_gen,
        total_labor_specialized_usd=tot_labor_spec,
        total_insumos_usd=tot_insumos,
        total_herramientas_usd=tot_herramientas,
        direct_cost_usd=direct_cost_usd,
        margin_percentage=dec_margin_pct,
        margin_usd=margin_usd,
        discount_usd=rounded_discount_usd,
        subtotal_usd=subtotal_usd,
        tax_percentage=dec_tax_pct,
        tax_usd=tax_usd,
        total_usd=total_usd,
        is_subtotal_valid=is_subtotal_valid,
        subtotal_error=subtotal_error,
    )
