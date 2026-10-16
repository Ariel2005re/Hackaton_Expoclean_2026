"""Pruebas unitarias para el servicio de vista previa y validador de emisión (B07 y B08).

Cubre RF-02, RF-03, RF-04, RF-12, RF-13, RF-18–RF-21, RF-23, RF-32 y RF-33.
"""

from datetime import date, time
from decimal import Decimal
import pytest

from backend.app.estimation.calendar import PeriodType
from backend.app.estimation.effort import InfrastructureState
from backend.app.estimation.pricing import ResourceKind, ResourceScope
from backend.app.estimation.preview import (
    ClientDraftInput,
    ServiceDraftInput,
    WorkTypeDraftInput,
    GroupDraftInput,
    ResourceDraftInput,
    QuoteDraftInput,
    generate_estimation_preview,
)


class TestPreviewAndValidationB07B08:
    """Pruebas para validación de emisión e integración de la vista previa."""

    def test_cotizacion_completa_y_valida_habilita_emision(self):
        """Una cotización con todos los datos requeridos habilita emisión y entrega vista previa completa."""
        client = ClientDraftInput(name="Empresa ABC", service_address="Av. Amazonas 123 y Colón")
        service = ServiceDraftInput(
            infrastructure_type="Oficinas",
            cleaning_type="Mantenimiento",
            start_date=date(2026, 3, 2),  # Lunes
            period_type=PeriodType.SEMANAL,
            start_time=time(8, 0),
            end_time=time(13, 0),  # 5 horas disponibles
        )
        group1 = GroupDraftInput(
            group_id="g1",
            name="Piso 1 - Oficinas",
            units_count=4,
            sqm_per_unit=Decimal("25.0"),  # 100 m² físicos
            service_days=["lunes", "miércoles", "viernes"],
            visits_per_day=1,
            state=InfrastructureState.BUENO,
            profile_id="perfil-oficinas",
            general_work=WorkTypeDraftInput(
                enabled=True,
                productivity_sqm_per_hour=Decimal("50.0"),  # 100 / 50 * 1 = 2 horas
                hourly_rate_usd=Decimal("6.00"),
                assigned_workers=1,
            ),
        )
        res1 = ResourceDraftInput(
            resource_id="r1",
            description="Limpiavidrios",
            kind=ResourceKind.INSUMO,
            scope=ResourceScope.GRUPO,
            group_id="g1",
            quantity=Decimal("0.5"),
            unit_cost_usd=Decimal("4.00"),
        )

        quote = QuoteDraftInput(
            quote_id="Q-001",
            client=client,
            service=service,
            groups=[group1],
            resources=[res1],
            margin_percentage=Decimal("10.0"),
            discount_usd=Decimal("0.00"),
            tax_percentage=Decimal("15.0"),
        )

        preview = generate_estimation_preview(quote)

        assert preview.can_save_draft is True
        assert preview.is_emission_valid is True
        assert len(preview.pending_emission_issues) == 0

        # Verificaciones de calendario (3 días en la semana)
        assert preview.calendar_summary is not None
        assert preview.calendar_summary.group_interventions["g1"] == 3
        assert preview.calendar_summary.shared_service_days_count == 3

        # Verificaciones de esfuerzo (2 horas de visita caben en ventana de 5 h)
        assert "g1" in preview.group_efforts
        assert preview.group_efforts["g1"].visit_duration_hours == Decimal("2.0")

        # Verificaciones de precio
        assert preview.pricing_summary is not None
        # Mano de obra: 2 h * 3 intervenciones = 6 h * $6.00 = $36.00
        assert preview.pricing_summary.total_labor_general_usd == Decimal("36.00")
        # Insumo: 0.5 * $4.00 * 3 = $6.00
        assert preview.pricing_summary.total_insumos_usd == Decimal("6.00")
        # Costo directo: 36 + 6 = 42.00
        assert preview.pricing_summary.direct_cost_usd == Decimal("42.00")
        # Margen: 42 * 10% = $4.20
        assert preview.pricing_summary.margin_usd == Decimal("4.20")
        # Subtotal: 42 + 4.20 = 46.20
        assert preview.pricing_summary.subtotal_usd == Decimal("46.20")
        # Impuesto: 46.20 * 15% = 6.93
        assert preview.pricing_summary.tax_usd == Decimal("6.93")
        # Total: 46.20 + 6.93 = 53.13
        assert preview.pricing_summary.total_usd == Decimal("53.13")

    def test_borrador_incompleto_se_puede_guardar_pero_bloquea_emision(self):
        """RF-13 y RF-22: Un borrador vacío se puede guardar pero reúne todos los pendientes de emisión."""
        empty_quote = QuoteDraftInput(quote_id="Q-EMPTY")
        preview = generate_estimation_preview(empty_quote)

        assert preview.can_save_draft is True
        assert preview.is_emission_valid is False
        assert len(preview.pending_emission_issues) > 0

        # Debe señalar cliente, servicio y falta de grupos
        issues_text = " ".join(preview.pending_emission_issues)
        assert "cliente" in issues_text
        assert "servicio" in issues_text
        assert "al menos un grupo" in issues_text

    def test_trabajo_especializado_sin_superficie_confirmada_bloquea_emision(self):
        """RF-13: Si incluye trabajo especializado, su superficie propia debe estar confirmada."""
        client = ClientDraftInput(name="Cliente Test", service_address="Calle 1")
        service = ServiceDraftInput(
            start_date=date(2026, 3, 2),
            period_type=PeriodType.SEMANAL,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        group_spec = GroupDraftInput(
            group_id="g_spec",
            name="Área especial",
            units_count=1,
            sqm_per_unit=Decimal("100"),
            service_days=["lunes"],
            visits_per_day=1,
            state=InfrastructureState.BUENO,
            profile_id="perfil-1",
            specialized_work=WorkTypeDraftInput(
                enabled=True,
                productivity_sqm_per_hour=Decimal("20"),
                hourly_rate_usd=Decimal("10"),
                custom_surface_sqm=None,  # ¡FALTA SUPERFICIE CONFIRMADA!
            ),
        )

        quote = QuoteDraftInput(
            quote_id="Q-SPEC",
            client=client,
            service=service,
            groups=[group_spec],
        )

        preview = generate_estimation_preview(quote)
        assert preview.is_emission_valid is False
        assert any("confirmar su superficie propia" in issue for issue in preview.pending_emission_issues)

    def test_suma_de_visitas_excede_ventana_bloquea_emision(self):
        """Criterio B04, B07 y RF-23: Si suma de duraciones excede horario, señala pendiente y bloquea PDF."""
        client = ClientDraftInput(name="Cliente Test", service_address="Calle 1")
        service = ServiceDraftInput(
            start_date=date(2026, 3, 2),
            period_type=PeriodType.SEMANAL,
            start_time=time(8, 0),
            end_time=time(11, 0),  # 3 horas de ventana disponible
        )
        # Visita estimada en 2 horas (100 m² / 50 m²/h = 2 h)
        group_exceed = GroupDraftInput(
            group_id="g_exc",
            name="Oficinas saturadas",
            units_count=1,
            sqm_per_unit=Decimal("100"),
            service_days=["lunes"],
            visits_per_day=2,  # 2 visitas * 2 horas = 4 horas > 3 horas de ventana!
            state=InfrastructureState.BUENO,
            profile_id="perfil-1",
            general_work=WorkTypeDraftInput(
                enabled=True,
                productivity_sqm_per_hour=Decimal("50"),
                hourly_rate_usd=Decimal("6"),
                assigned_workers=1,
            ),
        )

        quote = QuoteDraftInput(
            quote_id="Q-EXC",
            client=client,
            service=service,
            groups=[group_exceed],
        )

        preview = generate_estimation_preview(quote)
        assert preview.is_emission_valid is False
        assert any("excede la ventana de trabajo disponible" in issue for issue in preview.pending_emission_issues)

    def test_subtotal_no_positivo_bloquea_emision(self):
        """RF-21 y B07: Subtotal no positivo bloquea emisión y expone la causa."""
        client = ClientDraftInput(name="Cliente Test", service_address="Calle 1")
        service = ServiceDraftInput(
            start_date=date(2026, 3, 2),
            period_type=PeriodType.SEMANAL,
            start_time=time(8, 0),
            end_time=time(17, 0),
        )
        group = GroupDraftInput(
            group_id="g1",
            name="Local",
            units_count=1,
            sqm_per_unit=Decimal("50"),
            service_days=["lunes"],
            visits_per_day=1,
            state=InfrastructureState.BUENO,
            profile_id="perfil-1",
            general_work=WorkTypeDraftInput(
                enabled=True,
                productivity_sqm_per_hour=Decimal("50"),
                hourly_rate_usd=Decimal("10"),
                assigned_workers=1,
            ),
        )
        # Costo directo = 1 h * $10 = $10.00
        quote = QuoteDraftInput(
            quote_id="Q-SUBT",
            client=client,
            service=service,
            groups=[group],
            discount_usd=Decimal("50.00"),  # Descuento $50 > $10 costo directo
        )

        preview = generate_estimation_preview(quote)
        assert preview.is_emission_valid is False
        assert any("subtotal de la cotización debe ser positivo" in issue for issue in preview.pending_emission_issues)
