"""Pruebas unitarias para el motor de calendario e intervenciones (B01 y B02).

Cubre RF-03, RF-04, RF-20, RF-32 y RF-33.
"""

from datetime import date
import pytest

from backend.app.estimation.calendar import (
    PeriodType,
    GroupCalendarInput,
    calculate_period_limits,
    calculate_calendar_summary,
    normalize_weekday,
)


class TestPeriodLimitsB01:
    """Pruebas para cálculo de límites de período según RF-03 y RF-33."""

    def test_semanal_siete_dias_consecutivos(self):
        """Un período semanal debe abarcar exactamente 7 días inclusivos."""
        start = date(2026, 3, 2)  # Lunes
        start_lim, end_lim = calculate_period_limits(start, PeriodType.SEMANAL)
        assert start_lim == start
        assert end_lim == date(2026, 3, 8)  # Domingo
        assert (end_lim - start_lim).days + 1 == 7

    def test_quincenal_catorce_dias_consecutivos(self):
        """Un período quincenal debe abarcar exactamente 14 días inclusivos."""
        start = date(2026, 3, 2)
        start_lim, end_lim = calculate_period_limits(start, "quincenal")
        assert start_lim == start
        assert end_lim == date(2026, 3, 15)
        assert (end_lim - start_lim).days + 1 == 14

    def test_mensual_ejemplo_15_enero_a_14_febrero(self):
        """Ejemplo explícito de RF-03: del 15 de enero al 14 de febrero."""
        start = date(2026, 1, 15)
        start_lim, end_lim = calculate_period_limits(start, PeriodType.MENSUAL)
        assert start_lim == start
        assert end_lim == date(2026, 2, 14)

    def test_mensual_ejemplo_31_enero_ano_no_bisiesto(self):
        """Ejemplo explícito de RF-03: 31 de enero a 28 de febrero en año no bisiesto."""
        start = date(2026, 1, 31)
        start_lim, end_lim = calculate_period_limits(start, PeriodType.MENSUAL)
        assert start_lim == start
        assert end_lim == date(2026, 2, 28)

    def test_mensual_ejemplo_31_enero_ano_bisiesto(self):
        """Ejemplo explícito de RF-03: 31 de enero a 29 de febrero en año bisiesto (2024)."""
        start = date(2024, 1, 31)
        start_lim, end_lim = calculate_period_limits(start, PeriodType.MENSUAL)
        assert start_lim == start
        assert end_lim == date(2024, 2, 29)

    def test_mensual_comienzos_29_y_30_enero_sin_dia_equivalente(self):
        """RF-33: Período mensual que empieza el 29 o 30 y febrero no tiene ese día."""
        # En 2026 (no bisiesto, feb tiene 28 días):
        # 30 de enero -> feb no tiene 30 -> último día de feb = 28
        _, end_30 = calculate_period_limits(date(2026, 1, 30), PeriodType.MENSUAL)
        assert end_30 == date(2026, 2, 28)

        # 29 de enero en 2026 -> feb no tiene 29 -> último día de feb = 28
        _, end_29_nonleap = calculate_period_limits(date(2026, 1, 29), PeriodType.MENSUAL)
        assert end_29_nonleap == date(2026, 2, 28)

        # En 2024 (bisiesto, feb tiene 29 días):
        # 29 de enero en 2024 -> feb SÍ tiene 29 -> día anterior al equivalente es 28
        _, end_29_leap = calculate_period_limits(date(2024, 1, 29), PeriodType.MENSUAL)
        assert end_29_leap == date(2024, 2, 28)

        # 30 de enero en 2024 -> feb no tiene 30 -> último día de feb = 29
        _, end_30_leap = calculate_period_limits(date(2024, 1, 30), PeriodType.MENSUAL)
        assert end_30_leap == date(2024, 2, 29)

    def test_mensual_marzo_a_abril_mes_de_30_dias(self):
        """31 de marzo hacia abril (abril solo tiene 30 días, no 31)."""
        start = date(2026, 3, 31)
        _, end = calculate_period_limits(start, PeriodType.MENSUAL)
        assert end == date(2026, 4, 30)

    def test_mensual_cambio_de_ano(self):
        """Mes de diciembre que transiciona a enero del siguiente año."""
        start = date(2026, 12, 15)
        _, end = calculate_period_limits(start, PeriodType.MENSUAL)
        assert end == date(2027, 1, 14)

        # 31 de diciembre -> enero sí tiene 31 -> día anterior al equivalente = 30 de enero
        start_31 = date(2026, 12, 31)
        _, end_31 = calculate_period_limits(start_31, PeriodType.MENSUAL)
        assert end_31 == date(2027, 1, 30)

    def test_periodo_invalido_lanza_error(self):
        """Un período no reconocido debe lanzar ValueError."""
        with pytest.raises(ValueError, match="Período no reconocido"):
            calculate_period_limits(date(2026, 1, 1), "anual")


class TestCalendarSummaryB02:
    """Pruebas para conteo de intervenciones y jornadas compartidas según RF-04, RF-20 y RF-33."""

    def test_dos_grupos_mismo_dia_suman_visitas_pero_una_jornada_compartida(self):
        """Criterio de B02: dos grupos el mismo día suman sus visitas, pero solo una jornada compartida."""
        # Semana que empieza el lunes 2026-03-02 hasta el domingo 2026-03-08
        start = date(2026, 3, 2)
        # Grupo 1 atiende solo los lunes con 2 visitas por día
        g1 = GroupCalendarInput(group_id="oficinas", service_days=["lunes"], visits_per_day=2)
        # Grupo 2 atiende solo los lunes con 1 visita por día
        g2 = GroupCalendarInput(group_id="pasillos", service_days=["lunes"], visits_per_day=1)

        summary = calculate_calendar_summary(start, PeriodType.SEMANAL, [g1, g2])

        # En esa semana solo hay 1 lunes (2026-03-02)
        assert summary.group_interventions["oficinas"] == 2
        assert summary.group_interventions["pasillos"] == 1
        # Suma total de intervenciones = 3
        assert sum(summary.group_interventions.values()) == 3
        # Pero los recursos compartidos solo se cobran en las jornadas con servicio: exactamente 1 jornada
        assert summary.shared_service_days_count == 1
        assert summary.shared_service_dates == [date(2026, 3, 2)]

    def test_grupos_en_dias_distintos_y_dias_coincidentes(self):
        """Verifica conteo cuando hay días separados y días donde coinciden varios grupos."""
        start = date(2026, 3, 2)  # Lunes 2 de marzo al domingo 8 de marzo
        # G1: Lunes y Miércoles, 1 visita por día
        g1 = GroupCalendarInput(group_id="G1", service_days=["lunes", "miercoles"], visits_per_day=1)
        # G2: Miércoles y Viernes, 2 visitas por día
        g2 = GroupCalendarInput(group_id="G2", service_days=["miércoles", "viernes"], visits_per_day=2)

        summary = calculate_calendar_summary(start, PeriodType.SEMANAL, [g1, g2])

        # G1 tiene 2 visitas (lunes y miércoles)
        assert summary.group_interventions["G1"] == 2
        # G2 tiene 4 visitas (2 el miércoles + 2 el viernes)
        assert summary.group_interventions["G2"] == 4

        # Días con al menos un servicio: Lunes (G1), Miércoles (G1 + G2), Viernes (G2) = 3 días
        assert summary.shared_service_days_count == 3
        assert summary.shared_service_dates == [
            date(2026, 3, 2),  # Lunes
            date(2026, 3, 4),  # Miércoles
            date(2026, 3, 6),  # Viernes
        ]

    def test_mes_completo_con_multiples_semanas(self):
        """Verifica que un período mensual cuente todas las intervenciones en el rango."""
        # 1 de marzo 2026 (domingo) al 31 de marzo 2026 (martes) -> día antes del 1 de abril
        start = date(2026, 3, 1)
        g1 = GroupCalendarInput(group_id="aulas", service_days=["lunes", "martes"], visits_per_day=1)

        summary = calculate_calendar_summary(start, PeriodType.MENSUAL, [g1])

        # En marzo 2026 hay: 5 lunes (2, 9, 16, 23, 30) y 5 martes (3, 10, 17, 24, 31) = 10 días
        assert summary.group_interventions["aulas"] == 10
        assert summary.shared_service_days_count == 10

    def test_visitas_no_positivas_rechazadas(self):
        """RF-32: visitas por día debe ser entero positivo."""
        with pytest.raises(ValueError, match="entero positivo"):
            GroupCalendarInput(group_id="g1", service_days=["lunes"], visits_per_day=0)

        with pytest.raises(ValueError, match="entero positivo"):
            GroupCalendarInput(group_id="g1", service_days=["lunes"], visits_per_day=-1)

    def test_dia_invalido_rechazado(self):
        """Normalizar día inválido debe levantar ValueError."""
        with pytest.raises(ValueError, match="inválido"):
            normalize_weekday("findesemana")

        with pytest.raises(ValueError, match="inválido"):
            normalize_weekday(7)  # solo 0 a 6
