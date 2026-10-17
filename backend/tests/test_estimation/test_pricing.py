"""Pruebas unitarias para el motor de costeo, recursos, precios y redondeo (B05 y B06).

Cubre RF-18, RF-20, RF-21, RF-32 y RF-33.
"""

from decimal import Decimal
import pytest

from backend.app.estimation.pricing import (
    ResourceKind,
    ResourceScope,
    ResourceInput,
    LaborCostInput,
    calculate_pricing,
    round_half_up,
)


class TestPricingRoundingAndDecimalsB05B06:
    """Pruebas para redondeo mitad hacia arriba y costeo de recursos decimales."""

    def test_regla_redondeo_mitad_hacia_arriba(self):
        """RF-32: Regla de redondeo al centavo con regla de mitad hacia arriba (ROUND_HALF_UP)."""
        assert round_half_up(Decimal("10.005")) == Decimal("10.01")
        assert round_half_up(Decimal("10.004")) == Decimal("10.00")
        assert round_half_up(Decimal("10.015")) == Decimal("10.02")
        assert round_half_up(Decimal("10.025")) == Decimal("10.03")

    def test_recursos_decimales_y_distincion_grupo_vs_compartido(self):
        """Criterio B05: Cantidades decimales se cobran con recurrencia correcta sin duplicar compartidos."""
        # 10 intervenciones para el grupo 1
        group_interventions = {"g1": 10}
        # 4 jornadas compartidas en el período
        shared_days = 4

        # Insumo de grupo: 0.25 litros por intervención a $6.50
        res_grupo = ResourceInput(
            resource_id="desinfectante",
            description="Desinfectante concentrado",
            kind=ResourceKind.INSUMO,
            scope=ResourceScope.GRUPO,
            group_id="g1",
            quantity=Decimal("0.25"),
            unit_cost_usd=Decimal("6.50"),
        )

        # Herramienta compartida: 0.5 jornadas de uso por día con servicio a $20.00
        res_comp = ResourceInput(
            resource_id="aspiradora",
            description="Aspiradora industrial",
            kind=ResourceKind.HERRAMIENTA,
            scope=ResourceScope.COMPARTIDO,
            quantity=Decimal("0.5"),
            unit_cost_usd=Decimal("20.00"),
        )

        pricing = calculate_pricing(
            labor_inputs=[],
            resource_inputs=[res_grupo, res_comp],
            group_interventions=group_interventions,
            shared_service_days_count=shared_days,
            margin_percentage=Decimal("0"),
            discount_usd=Decimal("0"),
            tax_percentage=Decimal("0"),
        )

        # Insumo grupo: 0.25 * 6.50 * 10 = $16.25
        assert pricing.total_insumos_usd == Decimal("16.25")
        # Herramienta compartida: 0.5 * 20.00 * 4 = $40.00
        assert pricing.total_herramientas_usd == Decimal("40.00")
        assert pricing.direct_cost_usd == Decimal("56.25")

    def test_tabla_de_valores_esperados_reproduce_totales_al_centavo(self):
        """Criterio B06 y RF-21: Tabla completa esperada de costo directo, margen, descuento, impuesto y total."""
        # Mano de obra general: 25 horas totales a $5.50 = $137.50
        lab_gen = LaborCostInput(
            group_id="g1",
            group_name="Oficinas",
            work_type="general",
            hours_per_intervention=Decimal("2.5"),
            interventions_count=10,
            hourly_rate_usd=Decimal("5.50"),
        )
        # Mano de obra especializada: 12.5 horas totales a $10.00 = $125.00
        lab_spec = LaborCostInput(
            group_id="g1",
            group_name="Oficinas",
            work_type="especializado",
            hours_per_intervention=Decimal("1.25"),
            interventions_count=10,
            hourly_rate_usd=Decimal("10.00"),
        )
        # Insumo de grupo: 0.35 * 4.80 * 10 = $16.80
        res_grupo = ResourceInput(
            resource_id="ins_1",
            description="Detergente",
            kind=ResourceKind.INSUMO,
            scope=ResourceScope.GRUPO,
            group_id="g1",
            quantity=Decimal("0.35"),
            unit_cost_usd=Decimal("4.80"),
        )
        # Herramienta compartida: 1.0 * 15.25 * 8 jornadas = $122.00
        res_comp = ResourceInput(
            resource_id="her_1",
            description="Pulidora",
            kind=ResourceKind.HERRAMIENTA,
            scope=ResourceScope.COMPARTIDO,
            quantity=Decimal("1.0"),
            unit_cost_usd=Decimal("15.25"),
        )

        pricing = calculate_pricing(
            labor_inputs=[lab_gen, lab_spec],
            resource_inputs=[res_grupo, res_comp],
            group_interventions={"g1": 10},
            shared_service_days_count=8,
            margin_percentage=Decimal("15.0"),  # 15% margen
            discount_usd=Decimal("20.00"),      # $20 descuento fijo
            tax_percentage=Decimal("15.0"),     # 15% IVA
        )

        # 1. Mano de obra
        assert pricing.total_labor_general_usd == Decimal("137.50")
        assert pricing.total_labor_specialized_usd == Decimal("125.00")
        assert pricing.total_insumos_usd == Decimal("16.80")
        assert pricing.total_herramientas_usd == Decimal("122.00")

        # 2. Costo Directo = 137.50 + 125.00 + 16.80 + 122.00 = 401.30
        assert pricing.direct_cost_usd == Decimal("401.30")

        # 3. Margen = 401.30 * 15% = 60.195 -> $60.20 (Half up)
        assert pricing.margin_usd == Decimal("60.20")

        # 4. Descuento = $20.00
        assert pricing.discount_usd == Decimal("20.00")

        # 5. Subtotal = 401.30 + 60.20 - 20.00 = 441.50
        assert pricing.subtotal_usd == Decimal("441.50")
        assert pricing.is_subtotal_valid is True

        # 6. Impuesto = 441.50 * 15% = 66.225 -> $66.23 (Half up)
        assert pricing.tax_usd == Decimal("66.23")

        # 7. Total = 441.50 + 66.23 = 507.73
        assert pricing.total_usd == Decimal("507.73")

    def test_subtotal_no_positivo_detectado_y_bloqueante(self):
        """RF-21: Subtotal cero o negativo señala la causa e impide el PDF."""
        lab = LaborCostInput(
            group_id="g1",
            group_name="Oficinas",
            work_type="general",
            hours_per_intervention=Decimal("1.0"),
            interventions_count=1,
            hourly_rate_usd=Decimal("10.00"),  # Costo directo = 10.00
        )
        pricing = calculate_pricing(
            labor_inputs=[lab],
            resource_inputs=[],
            group_interventions={"g1": 1},
            shared_service_days_count=1,
            margin_percentage=Decimal("0"),
            discount_usd=Decimal("15.00"),  # Descuento mayor al costo -> Subtotal = -5.00
            tax_percentage=Decimal("15"),
        )

        assert pricing.subtotal_usd == Decimal("-5.00")
        assert pricing.is_subtotal_valid is False
        assert pricing.subtotal_error is not None
        assert "subtotal de la cotización debe ser positivo" in pricing.subtotal_error

    def test_magnitudes_negativas_rechazadas(self):
        """RF-32: Rechazar margen, descuento o impuesto negativos."""
        with pytest.raises(ValueError, match="margen .* negativo"):
            calculate_pricing([], [], {}, 0, margin_percentage=Decimal("-5"))

        with pytest.raises(ValueError, match="descuento .* negativo"):
            calculate_pricing([], [], {}, 0, discount_usd=Decimal("-10"))

        with pytest.raises(ValueError, match="impuesto .* negativo"):
            calculate_pricing([], [], {}, 0, tax_percentage=Decimal("-15"))
