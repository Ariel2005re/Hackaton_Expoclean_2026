"""Motor de cálculo de calendario, períodos e intervenciones para cotizaciones de limpieza.

Cumple con RF-03, RF-04, RF-20, RF-32 y RF-33 de specs/001-hackaton/spec.md.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Sequence, Set, Union


class PeriodType(str, Enum):
    """Tipos de período admitidos según RF-03."""
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"


# Mapeo de nombres de días en español a índices de datetime.date.weekday() (0=Lunes, 6=Domingo)
_WEEKDAY_MAP = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}


def normalize_weekday(day: Union[str, int]) -> int:
    """Normaliza un día de la semana a índice entero (0=Lunes ... 6=Domingo).

    Lanza ValueError si el valor no corresponde a un día válido.
    """
    if isinstance(day, int):
        if 0 <= day <= 6:
            return day
        raise ValueError(f"Índice de día de semana inválido: {day}. Debe estar entre 0 (Lunes) y 6 (Domingo).")
    
    if isinstance(day, str):
        cleaned = day.strip().lower()
        if cleaned in _WEEKDAY_MAP:
            return _WEEKDAY_MAP[cleaned]
        raise ValueError(f"Nombre de día de la semana inválido: '{day}'. Debe ser lunes, martes, miércoles, etc.")
    
    raise TypeError(f"Tipo no soportado para día de la semana: {type(day).__name__}")


def calculate_period_limits(start_date: date, period_type: Union[PeriodType, str]) -> tuple[date, date]:
    """Calcula la fecha de inicio y fin inclusivas del período según RF-03 y RF-33.

    - Período semanal: siete días consecutivos (inicio + 6 días).
    - Período quincenal: catorce días consecutivos (inicio + 13 días).
    - Período mensual: comienza en start_date y termina el día anterior al equivalente del mes siguiente.
      Si el día equivalente no existe en el mes siguiente (ej. 31 de enero hacia febrero),
      terminará el último día del mes siguiente (ej. 28 o 29 de febrero).

    Retorna: (fecha_inicio, fecha_fin_inclusiva).
    """
    if not isinstance(start_date, date):
        raise TypeError("start_date debe ser una instancia de datetime.date")

    if isinstance(period_type, str):
        try:
            p_type = PeriodType(period_type.lower().strip())
        except ValueError:
            raise ValueError(f"Período no reconocido: '{period_type}'. Debe ser semanal, quincenal o mensual.")
    elif isinstance(period_type, PeriodType):
        p_type = period_type
    else:
        raise TypeError(f"Tipo no soportado para period_type: {type(period_type).__name__}")

    if p_type == PeriodType.SEMANAL:
        return start_date, start_date + timedelta(days=6)

    if p_type == PeriodType.QUINCENAL:
        return start_date, start_date + timedelta(days=13)

    if p_type == PeriodType.MENSUAL:
        next_month = 1 if start_date.month == 12 else start_date.month + 1
        next_year = start_date.year + 1 if start_date.month == 12 else start_date.year
        days_in_next_month = calendar.monthrange(next_year, next_month)[1]

        if start_date.day <= days_in_next_month:
            equivalent_date = date(next_year, next_month, start_date.day)
            end_date = equivalent_date - timedelta(days=1)
        else:
            # Si ese día equivalente no existe, terminará el último día del mes siguiente
            end_date = date(next_year, next_month, days_in_next_month)

        return start_date, end_date

    raise ValueError(f"Período no soportado: {p_type}")


@dataclass
class GroupCalendarInput:
    """Parámetros de calendario para un grupo de espacios."""
    group_id: str
    service_days: Sequence[Union[str, int]]
    visits_per_day: int

    def __post_init__(self):
        if not self.group_id or not isinstance(self.group_id, str):
            raise ValueError("group_id debe ser un texto no vacío identificando al grupo.")
        if not isinstance(self.visits_per_day, int) or self.visits_per_day <= 0:
            raise ValueError(f"visits_per_day debe ser un entero positivo (> 0). Valor recibido: {self.visits_per_day}")


@dataclass
class CalendarSummary:
    """Resultado del cálculo de calendario del período."""
    start_date: date
    end_date: date
    period_type: PeriodType
    total_days: int
    group_interventions: dict[str, int]
    shared_service_days_count: int
    shared_service_dates: list[date]
    group_service_dates: dict[str, list[date]] = field(default_factory=dict)


def calculate_calendar_summary(
    start_date: date,
    period_type: Union[PeriodType, str],
    groups: Sequence[GroupCalendarInput],
) -> CalendarSummary:
    """Calcula intervenciones por grupo y jornadas compartidas durante el período (RF-04, RF-20, RF-33).

    - Cuenta por cada grupo una intervención por cada visita en los días que le correspondan.
    - No excluye feriados (RF-04).
    - Cuenta por separado los días distintos (jornadas únicas) con servicio de al menos un grupo (RF-33).
    """
    start_lim, end_lim = calculate_period_limits(start_date, period_type)
    resolved_period_type = PeriodType(period_type.lower().strip()) if isinstance(period_type, str) else period_type

    # Normalizar los días de servicio para cada grupo
    normalized_groups: list[tuple[GroupCalendarInput, Set[int]]] = []
    for g in groups:
        norm_days = {normalize_weekday(d) for d in g.service_days}
        normalized_groups.append((g, norm_days))

    group_interventions: dict[str, int] = {g.group_id: 0 for g in groups}
    group_service_dates: dict[str, list[date]] = {g.group_id: [] for g in groups}
    shared_service_dates: list[date] = []

    current_date = start_lim
    total_calendar_days = (end_lim - start_lim).days + 1

    while current_date <= end_lim:
        day_weekday = current_date.weekday()
        day_has_any_service = False

        for group, service_weekdays in normalized_groups:
            if day_weekday in service_weekdays:
                group_interventions[group.group_id] += group.visits_per_day
                group_service_dates[group.group_id].append(current_date)
                day_has_any_service = True

        if day_has_any_service:
            shared_service_dates.append(current_date)

        current_date += timedelta(days=1)

    return CalendarSummary(
        start_date=start_lim,
        end_date=end_lim,
        period_type=resolved_period_type,
        total_days=total_calendar_days,
        group_interventions=group_interventions,
        shared_service_days_count=len(shared_service_dates),
        shared_service_dates=shared_service_dates,
        group_service_dates=group_service_dates,
    )
