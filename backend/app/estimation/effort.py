"""Cálculo de esfuerzo físico, superficies, dotación y duración de visitas.

Cumple con RF-03, RF-04, RF-12, RF-16, RF-18, RF-19, RF-23 y RF-32.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Union


class InfrastructureState(str, Enum):
    """Estado de la infraestructura según RF-04."""
    BUENO = "bueno"
    REGULAR = "regular"
    MALO = "malo"


DEFAULT_STATE_FACTORS: dict[InfrastructureState, Decimal] = {
    InfrastructureState.BUENO: Decimal("1.00"),
    InfrastructureState.REGULAR: Decimal("1.25"),
    InfrastructureState.MALO: Decimal("1.50"),
}


def to_decimal(val: Union[int, float, str, Decimal], name: str = "valor") -> Decimal:
    """Convierte un valor numérico a Decimal de forma segura."""
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception as e:
        raise ValueError(f"No se pudo convertir {name}='{val}' a Decimal: {e}")


@dataclass
class WorkTypeEffortInput:
    """Configuración de trabajo (general o especializado) para un grupo de espacios."""
    enabled: bool
    productivity_sqm_per_hour: Decimal  # m²/h, debe ser > 0 si enabled=True
    hourly_rate_usd: Decimal            # USD/h, debe ser > 0 si enabled=True
    assigned_workers: int = 1           # Entero positivo > 0
    custom_surface_sqm: Optional[Decimal] = None  # Para especializado, superficie propia confirmada
    adjusted_hours_per_intervention: Optional[Decimal] = None  # Ajuste manual opcional de horas totales

    def __post_init__(self):
        if self.enabled:
            self.productivity_sqm_per_hour = to_decimal(self.productivity_sqm_per_hour, "rendimiento")
            self.hourly_rate_usd = to_decimal(self.hourly_rate_usd, "tarifa")
            if self.custom_surface_sqm is not None:
                self.custom_surface_sqm = to_decimal(self.custom_surface_sqm, "superficie especializada")
            if self.adjusted_hours_per_intervention is not None:
                self.adjusted_hours_per_intervention = to_decimal(self.adjusted_hours_per_intervention, "horas ajustadas")

            if self.productivity_sqm_per_hour <= Decimal("0"):
                raise ValueError(f"El rendimiento en m²/h debe ser positivo (> 0). Recibido: {self.productivity_sqm_per_hour}")
            if self.hourly_rate_usd <= Decimal("0"):
                raise ValueError(f"La tarifa horaria en USD debe ser positiva (> 0). Recibida: {self.hourly_rate_usd}")
            if not isinstance(self.assigned_workers, int) or self.assigned_workers <= 0:
                raise ValueError(f"La dotación de personas debe ser un entero positivo (> 0). Recibido: {self.assigned_workers}")
            if self.custom_surface_sqm is not None and self.custom_surface_sqm <= Decimal("0"):
                raise ValueError(f"La superficie especializada debe ser positiva (> 0). Recibida: {self.custom_surface_sqm}")
            if self.adjusted_hours_per_intervention is not None and self.adjusted_hours_per_intervention <= Decimal("0"):
                raise ValueError(f"Las horas ajustadas deben ser positivas (> 0). Recibido: {self.adjusted_hours_per_intervention}")


@dataclass
class WorkTypeEffortResult:
    """Resultado del cálculo de esfuerzo para un tipo de trabajo."""
    surface_sqm: Decimal
    productivity_sqm_per_hour: Decimal
    hourly_rate_usd: Decimal
    state_factor: Decimal
    estimated_base_hours: Decimal
    total_hours_per_intervention: Decimal
    assigned_workers: int
    duration_hours: Decimal  # total_hours / workers


@dataclass
class GroupEffortResult:
    """Resultado del cálculo de esfuerzo y duración para un grupo de espacios."""
    group_id: str
    physical_sqm: Decimal
    state: InfrastructureState
    state_factor: Decimal
    general: Optional[WorkTypeEffortResult]
    specialized: Optional[WorkTypeEffortResult]
    visit_duration_hours: Decimal  # Mayor duración de los tipos que trabajan en simultáneo


def calculate_group_effort(
    group_id: str,
    units_count: int,
    sqm_per_unit: Union[int, float, str, Decimal],
    state: Union[InfrastructureState, str],
    general_config: Optional[WorkTypeEffortInput] = None,
    specialized_config: Optional[WorkTypeEffortInput] = None,
    custom_state_factor: Optional[Union[int, float, str, Decimal]] = None,
) -> GroupEffortResult:
    """Calcula m² físicos, horas por intervención, dotación y duración de visita (RF-04, RF-12, RF-18, RF-19).

    - Trabajo general usa m² físicos = units_count * sqm_per_unit.
    - Trabajo especializado usa su superficie propia confirmada.
    - Las horas base son: superficie ÷ rendimiento × factor_estado.
    - La duración de un tipo es: horas_totales ÷ dotación_personas.
    - La duración de la visita es la mayor entre general y especializado (trabajo simultáneo).
    """
    if not isinstance(units_count, int) or units_count <= 0:
        raise ValueError(f"La cantidad de unidades debe ser un entero positivo (> 0). Recibido: {units_count}")

    dec_sqm_per_unit = to_decimal(sqm_per_unit, "m² por unidad")
    if dec_sqm_per_unit <= Decimal("0"):
        raise ValueError(f"Los m² por unidad deben ser positivos (> 0). Recibido: {dec_sqm_per_unit}")

    physical_sqm = Decimal(units_count) * dec_sqm_per_unit

    res_state = InfrastructureState(state.lower().strip()) if isinstance(state, str) else state

    if custom_state_factor is not None:
        state_factor = to_decimal(custom_state_factor, "factor de estado")
    else:
        state_factor = DEFAULT_STATE_FACTORS[res_state]

    if state_factor <= Decimal("0"):
        raise ValueError(f"El factor de estado debe ser positivo (> 0). Recibido: {state_factor}")

    # Al menos un tipo de trabajo debe estar activo (RF-13)
    gen_active = general_config is not None and general_config.enabled
    spec_active = specialized_config is not None and specialized_config.enabled

    if not gen_active and not spec_active:
        raise ValueError("El grupo debe tener al menos un tipo de trabajo activo (general, especializado o ambos).")

    res_gen: Optional[WorkTypeEffortResult] = None
    if gen_active and general_config:
        base_h = (physical_sqm / general_config.productivity_sqm_per_hour) * state_factor
        total_h = general_config.adjusted_hours_per_intervention if general_config.adjusted_hours_per_intervention is not None else base_h
        dur_h = total_h / Decimal(general_config.assigned_workers)
        res_gen = WorkTypeEffortResult(
            surface_sqm=physical_sqm,
            productivity_sqm_per_hour=general_config.productivity_sqm_per_hour,
            hourly_rate_usd=general_config.hourly_rate_usd,
            state_factor=state_factor,
            estimated_base_hours=base_h,
            total_hours_per_intervention=total_h,
            assigned_workers=general_config.assigned_workers,
            duration_hours=dur_h,
        )

    res_spec: Optional[WorkTypeEffortResult] = None
    if spec_active and specialized_config:
        if specialized_config.custom_surface_sqm is None:
            raise ValueError("El trabajo especializado requiere una superficie propia confirmada en m².")
        spec_surface = specialized_config.custom_surface_sqm
        base_h = (spec_surface / specialized_config.productivity_sqm_per_hour) * state_factor
        total_h = specialized_config.adjusted_hours_per_intervention if specialized_config.adjusted_hours_per_intervention is not None else base_h
        dur_h = total_h / Decimal(specialized_config.assigned_workers)
        res_spec = WorkTypeEffortResult(
            surface_sqm=spec_surface,
            productivity_sqm_per_hour=specialized_config.productivity_sqm_per_hour,
            hourly_rate_usd=specialized_config.hourly_rate_usd,
            state_factor=state_factor,
            estimated_base_hours=base_h,
            total_hours_per_intervention=total_h,
            assigned_workers=specialized_config.assigned_workers,
            duration_hours=dur_h,
        )

    # Duración de la visita: mayor duración entre general y especializado (simultaneidad RF-19)
    durations = []
    if res_gen:
        durations.append(res_gen.duration_hours)
    if res_spec:
        durations.append(res_spec.duration_hours)
    visit_duration = max(durations) if durations else Decimal("0")

    return GroupEffortResult(
        group_id=group_id,
        physical_sqm=physical_sqm,
        state=res_state,
        state_factor=state_factor,
        general=res_gen,
        specialized=res_spec,
        visit_duration_hours=visit_duration,
    )


def calculate_daily_window_hours(start_time: time, end_time: time) -> Decimal:
    """Calcula la duración en horas de la ventana diaria de trabajo dentro del mismo día (RF-03).

    Lanza ValueError si el horario no tiene fin posterior a inicio en el mismo día.
    """
    if not isinstance(start_time, time) or not isinstance(end_time, time):
        raise TypeError("start_time y end_time deben ser instancias de datetime.time")

    start_minutes = start_time.hour * 60 + start_time.minute + start_time.second / 60
    end_minutes = end_time.hour * 60 + end_time.minute + end_time.second / 60

    if end_minutes <= start_minutes:
        raise ValueError(
            f"El horario debe tener fin posterior al inicio dentro del mismo día (no se admiten turnos nocturnos). "
            f"Inicio: {start_time}, Fin: {end_time}"
        )

    duration_minutes = end_minutes - start_minutes
    return Decimal(str(duration_minutes)) / Decimal("60")


def check_daily_window_fit(
    visit_duration_hours: Decimal,
    visits_per_day: int,
    start_time: time,
    end_time: time,
) -> tuple[bool, Decimal, Decimal]:
    """Comprueba si la suma de duraciones de las visitas del día cabe en la ventana horaria (RF-23).

    Retorna: (cabe: bool, duracion_diaria_total: Decimal, ventana_disponible_horas: Decimal).
    """
    if visits_per_day <= 0:
        raise ValueError(f"visits_per_day debe ser positivo (> 0). Recibido: {visits_per_day}")

    window_hours = calculate_daily_window_hours(start_time, end_time)
    daily_duration = visit_duration_hours * Decimal(visits_per_day)

    fits = daily_duration <= window_hours
    return fits, daily_duration, window_hours
