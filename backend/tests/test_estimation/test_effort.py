"""Pruebas unitarias para cálculo de esfuerzo, superficies, dotación y ventana diaria (B03 y B04).

Cubre RF-03, RF-04, RF-12, RF-16, RF-18, RF-19, RF-23 y RF-32.
"""

from datetime import time
from decimal import Decimal
import pytest

from backend.app.estimation.effort import (
    InfrastructureState,
    WorkTypeEffortInput,
    calculate_group_effort,
    calculate_daily_window_hours,
    check_daily_window_fit,
)


class TestEffortB03:
    """Pruebas para cálculo de superficies y horas por tipo de trabajo."""

    def test_separacion_superficie_general_y_especializada(self):
        """RF-12 y RF-18: Trabajo general usa m² físicos y especializado usa superficie propia."""
        # 8 oficinas de 35 m² = 280 m² físicos
        general = WorkTypeEffortInput(
            enabled=True,
            productivity_sqm_per_hour=Decimal("50.0"),  # 50 m²/h
            hourly_rate_usd=Decimal("6.50"),
            assigned_workers=1,
        )
        specialized = WorkTypeEffortInput(
            enabled=True,
            productivity_sqm_per_hour=Decimal("20.0"),  # 20 m²/h
            hourly_rate_usd=Decimal("10.00"),
            assigned_workers=1,
            custom_surface_sqm=Decimal("60.0"),  # Solo 60 m² de alfombra/vidrio
        )

        res = calculate_group_effort(
            group_id="oficinas_piso1",
            units_count=8,
            sqm_per_unit=Decimal("35.0"),
            state=InfrastructureState.REGULAR,  # Factor 1.25
            general_config=general,
            specialized_config=specialized,
        )

        assert res.physical_sqm == Decimal("280.0")
        assert res.state_factor == Decimal("1.25")

        # General: 280 / 50 * 1.25 = 7.0 horas
        assert res.general is not None
        assert res.general.surface_sqm == Decimal("280.0")
        assert res.general.estimated_base_hours == Decimal("7.0")
        assert res.general.total_hours_per_intervention == Decimal("7.0")

        # Especializado: 60 / 20 * 1.25 = 3.75 horas
        assert res.specialized is not None
        assert res.specialized.surface_sqm == Decimal("60.0")
        assert res.specialized.estimated_base_hours == Decimal("3.75")
        assert res.specialized.total_hours_per_intervention == Decimal("3.75")

    def test_factores_iniciales_bueno_regular_malo(self):
        """RF-16: Factores iniciales 1,00; 1,25; 1,50."""
        gen = WorkTypeEffortInput(
            enabled=True,
            productivity_sqm_per_hour=Decimal("100"),
            hourly_rate_usd=Decimal("5"),
        )
        res_b = calculate_group_effort("g", 1, 100, InfrastructureState.BUENO, general_config=gen)
        assert res_b.state_factor == Decimal("1.00")
        assert res_b.general.estimated_base_hours == Decimal("1.00")

        res_r = calculate_group_effort("g", 1, 100, InfrastructureState.REGULAR, general_config=gen)
        assert res_r.state_factor == Decimal("1.25")
        assert res_r.general.estimated_base_hours == Decimal("1.25")

        res_m = calculate_group_effort("g", 1, 100, InfrastructureState.MALO, general_config=gen)
        assert res_m.state_factor == Decimal("1.50")
        assert res_m.general.estimated_base_hours == Decimal("1.50")

    def test_rechazo_valores_no_positivos(self):
        """RF-32: Rechazar magnitudes no positivas donde se exige número positivo."""
        # Unidades <= 0
        with pytest.raises(ValueError, match="entero positivo"):
            calculate_group_effort("g", 0, 50, InfrastructureState.BUENO)

        # Superficie unitaria <= 0
        with pytest.raises(ValueError, match="positivos"):
            calculate_group_effort("g", 1, -10, InfrastructureState.BUENO)

        # Rendimiento <= 0
        with pytest.raises(ValueError, match="rendimiento .* positivo"):
            WorkTypeEffortInput(enabled=True, productivity_sqm_per_hour=Decimal("0"), hourly_rate_usd=Decimal("5"))

        # Tarifa <= 0
        with pytest.raises(ValueError, match="tarifa .* positiva"):
            WorkTypeEffortInput(enabled=True, productivity_sqm_per_hour=Decimal("50"), hourly_rate_usd=Decimal("-5"))

        # Dotación <= 0
        with pytest.raises(ValueError, match="dotación .* entero positivo"):
            WorkTypeEffortInput(enabled=True, productivity_sqm_per_hour=Decimal("50"), hourly_rate_usd=Decimal("5"), assigned_workers=0)

        # Superficie especializada requerida pero ausente
        with pytest.raises(ValueError, match="superficie propia confirmada"):
            spec_no_surface = WorkTypeEffortInput(enabled=True, productivity_sqm_per_hour=Decimal("20"), hourly_rate_usd=Decimal("10"))
            calculate_group_effort("g", 1, 100, InfrastructureState.BUENO, specialized_config=spec_no_surface)


class TestStaffingAndDailyWindowB04:
    """Pruebas para dotación de personal, simultaneidad y comprobación de ventana horaria."""

    def test_cambiar_solo_dotacion_mantiene_horas_totales(self):
        """RF-19: Cambiar dotación divide duración pero mantiene intactas las horas totales."""
        # Supongamos trabajo de 6 horas totales
        gen_1_worker = WorkTypeEffortInput(
            enabled=True,
            productivity_sqm_per_hour=Decimal("50"),
            hourly_rate_usd=Decimal("6.00"),
            assigned_workers=1,
            adjusted_hours_per_intervention=Decimal("6.0"),
        )
        res_1 = calculate_group_effort("g", 1, 100, InfrastructureState.BUENO, general_config=gen_1_worker)
        assert res_1.general.total_hours_per_intervention == Decimal("6.0")
        assert res_1.general.duration_hours == Decimal("6.0")
        assert res_1.visit_duration_hours == Decimal("6.0")

        # Con 2 personas: las horas totales siguen siendo 6.0, pero la duración se reduce a 3.0 h
        gen_2_workers = WorkTypeEffortInput(
            enabled=True,
            productivity_sqm_per_hour=Decimal("50"),
            hourly_rate_usd=Decimal("6.00"),
            assigned_workers=2,
            adjusted_hours_per_intervention=Decimal("6.0"),
        )
        res_2 = calculate_group_effort("g", 1, 100, InfrastructureState.BUENO, general_config=gen_2_workers)
        assert res_2.general.total_hours_per_intervention == Decimal("6.0")  # Mismas horas a facturar
        assert res_2.general.duration_hours == Decimal("3.0")                # Mitad de tiempo de permanencia
        assert res_2.visit_duration_hours == Decimal("3.0")

    def test_duracion_simultanea_ambos_tipos_usa_el_maximo(self):
        """RF-19: En una visita con general y especializado, la duración es el máximo de ambas."""
        gen = WorkTypeEffortInput(
            enabled=True,
            productivity_sqm_per_hour=Decimal("50"),
            hourly_rate_usd=Decimal("6.00"),
            assigned_workers=1,
            adjusted_hours_per_intervention=Decimal("4.0"),  # Duración = 4.0 h
        )
        spec = WorkTypeEffortInput(
            enabled=True,
            productivity_sqm_per_hour=Decimal("20"),
            hourly_rate_usd=Decimal("10.00"),
            custom_surface_sqm=Decimal("50"),
            assigned_workers=2,
            adjusted_hours_per_intervention=Decimal("5.0"),  # Duración = 5.0 / 2 = 2.5 h
        )
        res = calculate_group_effort("g", 1, 100, InfrastructureState.BUENO, general_config=gen, specialized_config=spec)
        assert res.general.duration_hours == Decimal("4.0")
        assert res.specialized.duration_hours == Decimal("2.5")
        # Máximo de ambos equipos operando en paralelo:
        assert res.visit_duration_hours == Decimal("4.0")

    def test_calculo_ventana_horaria_diaria(self):
        """RF-03: Ventana horaria dentro del mismo día."""
        start_t = time(8, 0)
        end_t = time(12, 30)
        hours = calculate_daily_window_hours(start_t, end_t)
        assert hours == Decimal("4.5")

        # Fin anterior o igual a inicio (o cruce de medianoche no admitido)
        with pytest.raises(ValueError, match="fin posterior al inicio"):
            calculate_daily_window_hours(time(20, 0), time(4, 0))

        with pytest.raises(ValueError, match="fin posterior al inicio"):
            calculate_daily_window_hours(time(10, 0), time(10, 0))

    def test_dos_visitas_que_juntas_exceden_la_ventana_bloquean_emision(self):
        """Criterio B04 y RF-23: dos visitas que individualmente caben pero sumadas exceden la ventana fallan."""
        # Ventana de 4 horas (08:00 a 12:00)
        start_t = time(8, 0)
        end_t = time(12, 0)

        # Visita estimada en 2.5 horas
        visit_duration = Decimal("2.5")

        # Con 1 visita al día: 2.5 h <= 4.0 h -> Cabe
        fits_1, daily_1, window = check_daily_window_fit(visit_duration, visits_per_day=1, start_time=start_t, end_time=end_t)
        assert fits_1 is True
        assert daily_1 == Decimal("2.5")
        assert window == Decimal("4.0")

        # Con 2 visitas al día: 2.5 * 2 = 5.0 h > 4.0 h -> ¡NO cabe! Bloquea emisión
        fits_2, daily_2, window = check_daily_window_fit(visit_duration, visits_per_day=2, start_time=start_t, end_time=end_t)
        assert fits_2 is False
        assert daily_2 == Decimal("5.0")
        assert window == Decimal("4.0")
