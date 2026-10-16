"""Módulo de Estimación, Calendario, Costeo y Validación (P2).

Exporta las funciones y estructuras acordadas en el contrato de integración.
"""

from backend.app.estimation.calendar import (
    PeriodType,
    GroupCalendarInput,
    CalendarSummary,
    calculate_period_limits,
    calculate_calendar_summary,
    normalize_weekday,
)
from backend.app.estimation.effort import (
    InfrastructureState,
    DEFAULT_STATE_FACTORS,
    WorkTypeEffortInput,
    WorkTypeEffortResult,
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
    CostLine,
    LaborCostInput,
    PricingSummary,
    calculate_pricing,
    round_half_up,
)
from backend.app.estimation.preview import (
    ClientDraftInput,
    ServiceDraftInput,
    WorkTypeDraftInput,
    GroupDraftInput,
    ResourceDraftInput,
    QuoteDraftInput,
    EstimationPreviewResult,
    generate_estimation_preview,
)

__all__ = [
    # Calendario (B01, B02)
    "PeriodType",
    "GroupCalendarInput",
    "CalendarSummary",
    "calculate_period_limits",
    "calculate_calendar_summary",
    "normalize_weekday",
    # Esfuerzo y Dotación (B03, B04)
    "InfrastructureState",
    "DEFAULT_STATE_FACTORS",
    "WorkTypeEffortInput",
    "WorkTypeEffortResult",
    "GroupEffortResult",
    "calculate_group_effort",
    "calculate_daily_window_hours",
    "check_daily_window_fit",
    "to_decimal",
    # Precios y Redondeo (B05, B06)
    "ResourceKind",
    "ResourceScope",
    "ResourceInput",
    "CostLine",
    "LaborCostInput",
    "PricingSummary",
    "calculate_pricing",
    "round_half_up",
    # Vista Previa y Validación de Emisión (B07, B08)
    "ClientDraftInput",
    "ServiceDraftInput",
    "WorkTypeDraftInput",
    "GroupDraftInput",
    "ResourceDraftInput",
    "QuoteDraftInput",
    "EstimationPreviewResult",
    "generate_estimation_preview",
]
