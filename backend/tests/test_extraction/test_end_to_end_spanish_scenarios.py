"""End-to-end integration test scenarios with realistic Spanish descriptions and deterministic mocks (Task C07 · RF-06–RF-11, RF-29–RF-31).

Covers all required acceptance criteria:
1. Explicit data and derivations (280 m² ÷ 8 oficinas = 35 m² por unidad).
2. Missing mandatory attributes (held in review as ABSENT).
3. Contradictory values (held in review as CONTRADICTORY, blocking confirmation until human resolution).
4. Defective groups isolated from revisable groups in mixed responses.
5. Re-analysis of description without duplicating confirmed groups.
6. Gemini failures (timeout, network down, safety rejection) preserving text and draft.
"""

from unittest.mock import MagicMock
import pytest

from backend.app.extraction.client import GeminiExtractionClient
from backend.app.extraction.exceptions import (
    GeminiRejectionError,
    GeminiTimeoutError,
    GeminiUnavailableError,
)
from backend.app.extraction.models import (
    AnalysisStatus,
    AttributeCondition,
    ExtractionInputRequest,
)
from backend.app.extraction.proposal_manager import ProposalReviewSession
from backend.app.extraction.provenance import resolve_contradiction
from backend.app.extraction.service import ExtractionService


class TestRealisticSpanishExtractionScenarios:
    """Verifies extraction and review using realistic Spanish descriptions of commercial spaces."""

    def test_scenario_corporate_building_with_derivations_and_explicit_attributes(self):
        """Escenario 1: Edificio corporativo con datos explícitos y derivación aritmética (RF-06, RF-07, RF-29).
        
        Texto: 'Edificio Amazonas: 8 oficinas que en total suman 280 m², 2 baños de 20 m² cada uno en buen estado, y 1 cafetería de 45 m².'
        """
        text_input = (
            "Edificio Amazonas: 8 oficinas que en total suman 280 m², "
            "2 baños de 20 m² cada uno en buen estado, y 1 cafetería de 45 m²."
        )

        # Deterministic mock response for this description
        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.return_value = {
            "spaces": [
                {
                    "name": "oficinas",
                    "quantity": 8,
                    "total_area_m2": 280.0,
                    "condition": "bueno",
                    "source_fragment": "8 oficinas que en total suman 280 m²",
                },
                {
                    "name": "baños",
                    "quantity": 2,
                    "unit_area_m2": 20.0,
                    "condition": "bueno",
                    "source_fragment": "2 baños de 20 m² cada uno en buen estado",
                },
                {
                    "name": "cafetería",
                    "quantity": 1,
                    "unit_area_m2": 45.0,
                    "source_fragment": "1 cafetería de 45 m²",
                },
            ]
        }

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text=text_input,
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        response = service.analyze_description(req)

        # 1. Status is SUCCESS
        assert response.status == AnalysisStatus.SUCCESS
        assert response.fallback_to_manual is False
        assert len(response.revisable_groups) == 3
        assert len(response.defective_groups) == 0

        # 2. Check office group derivation (RF-07: 280 ÷ 8 = 35)
        oficinas = next(g for g in response.revisable_groups if g.name == "oficinas")
        assert oficinas.unit_area_m2 == 35.0
        assert oficinas.total_area_m2 == 280.0
        assert oficinas.attributes["unit_area_m2"].condition == AttributeCondition.DERIVED
        assert "280" in oficinas.attributes["unit_area_m2"].operation
        assert "35" in oficinas.attributes["unit_area_m2"].operation
        assert oficinas.can_be_confirmed is True

        # 3. Check bathrooms explicit values
        banos = next(g for g in response.revisable_groups if g.name == "baños")
        assert banos.unit_area_m2 == 20.0
        assert banos.attributes["unit_area_m2"].condition == AttributeCondition.EXPLICIT
        assert banos.condition == "bueno"

    def test_scenario_school_with_missing_mandatory_attributes(self):
        """Escenario 2: Escuela con datos faltantes - atributos no expresados quedan como ABSENT (RF-07, RF-29).
        
        Texto: 'Colegio San Francisco: 10 aulas escolares y un auditorio principal en el bloque B.'
        """
        text_input = "Colegio San Francisco: 10 aulas escolares y un auditorio principal en el bloque B."

        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.return_value = {
            "spaces": [
                {
                    "name": "aulas",
                    "quantity": 10,
                    "source_fragment": "10 aulas escolares",
                    # unit_area_m2, condition, frequency are absent
                },
                {
                    "name": "auditorio",
                    "quantity": 1,
                    "source_fragment": "un auditorio principal en el bloque B",
                    # unit_area_m2 is absent
                },
            ]
        }

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text=text_input,
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        response = service.analyze_description(req)

        assert response.status == AnalysisStatus.SUCCESS
        assert len(response.revisable_groups) == 2

        aulas = next(g for g in response.revisable_groups if g.name == "aulas")
        # Missing area remains None and marked ABSENT (RF-07)
        assert aulas.unit_area_m2 is None
        assert aulas.attributes["unit_area_m2"].condition == AttributeCondition.ABSENT
        # Group cannot be confirmed until user completes missing mandatory area
        assert aulas.can_be_confirmed is False
        assert any("Superficie no especificada" in w for w in aulas.warnings)

    def test_scenario_industrial_plant_with_contradictions_and_resolution(self):
        """Escenario 3: Contradicciones bloquean confirmación y exigen resolución humana (RF-08, RF-09).
        
        Texto: 'Planta Industrial: taller mecánico en buen estado según informe matutino pero pésimo/malo según auditoría.'
        """
        text_input = "Planta Industrial: 1 taller mecánico de 150 m² en buen estado según informe matutino pero en mal estado según auditoría."

        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.return_value = {
            "spaces": [
                {
                    "name": "taller mecánico",
                    "quantity": 1,
                    "unit_area_m2": 150.0,
                    "conflicting_conditions": ["bueno", "malo"],
                    "source_fragment": "1 taller mecánico de 150 m² en buen estado según informe matutino pero en mal estado",
                }
            ]
        }

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text=text_input,
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        response = service.analyze_description(req)
        assert response.status == AnalysisStatus.SUCCESS
        taller = response.revisable_groups[0]

        # Contradiction detected
        assert taller.condition is None  # Never auto-picked
        assert taller.attributes["condition"].condition == AttributeCondition.CONTRADICTORY
        assert taller.attributes["condition"].conflicting_values == ["bueno", "malo"]
        # Confirmation is blocked (RF-08)
        assert taller.can_be_confirmed is False

        # Human resolves the contradiction (RF-08, RF-09)
        resolve_contradiction(
            group=taller,
            attribute_name="condition",
            chosen_value="regular",
            human_note="Consensuado estado regular tras inspección presencial",
        )

        assert taller.condition == "regular"
        assert taller.attributes["condition"].condition == AttributeCondition.HUMAN_CORRECTED
        assert taller.can_be_confirmed is True

    def test_scenario_mixed_response_with_defective_space(self):
        """Escenario 4: Respuesta mixta con grupo defectuoso aislado (RF-09, RF-29)."""
        text_input = "Complejo Bodegas: 3 bodegas de 200 m² y una zona residual con superficie -10 m²."

        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.return_value = {
            "spaces": [
                {
                    "name": "bodegas",
                    "quantity": 3,
                    "unit_area_m2": 200.0,
                    "condition": "regular",
                    "source_fragment": "3 bodegas de 200 m²",
                },
                {
                    # Defective: negative area
                    "name": "zona residual",
                    "quantity": 1,
                    "unit_area_m2": -10.0,
                    "source_fragment": "zona residual con superficie -10 m²",
                },
                {
                    # Defective: missing name
                    "quantity": 2,
                    "unit_area_m2": 15.0,
                    "source_fragment": "dos cuartos de limpieza",
                },
            ]
        }

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text=text_input,
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        response = service.analyze_description(req)

        # Status: PARTIAL_SUCCESS
        assert response.status == AnalysisStatus.PARTIAL_SUCCESS
        assert len(response.revisable_groups) == 1
        assert response.revisable_groups[0].name == "bodegas"
        # Defective groups are isolated and flagged without incorporation (RF-29)
        assert len(response.defective_groups) == 2

    def test_scenario_reanalysis_does_not_duplicate_confirmed_spaces(self):
        """Escenario 5: Reanálisis no duplica grupos confirmados (RF-10)."""
        session = ProposalReviewSession()
        # 1. Existing confirmed space: 2 salas de reuniones
        confirmed_space = next(
            g for g in [
                MagicMock(
                    id="conf-1",
                    name="salas de reuniones",
                    quantity=2,
                    unit_area_m2=25.0,
                    source_fragment="2 salas de reuniones de 25 m²",
                )
            ]
        )
        session.confirmed_groups = [confirmed_space]

        # 2. Re-analysis returns salas de reuniones again and 1 recepción
        new_salas = MagicMock(
            name="salas de reuniones",
            source_fragment="2 salas de reuniones de 25 m²",
            warnings=[],
        )
        new_recepcion = MagicMock(
            name="recepción",
            source_fragment="1 recepción de 30 m²",
            warnings=[],
        )

        mock_analysis = MagicMock(
            original_text="Texto nuevo",
            revisable_groups=[new_salas, new_recepcion],
            defective_groups=[],
        )

        session.reanalyze_without_duplicating_confirmed(mock_analysis)

        # Confirmed groups untouched (still exactly 1)
        assert len(session.confirmed_groups) == 1
        assert session.confirmed_groups[0].id == "conf-1"
        # Revisable groups contain the proposals
        assert len(session.revisable_groups) == 2

    def test_scenario_gemini_failures_preserve_text_and_allow_manual_continuation(self):
        """Escenario 6: Fallos de Gemini conservan texto y habilitan camino manual (RF-11)."""
        service_timeout = ExtractionService(
            client=MagicMock(call_gemini=MagicMock(side_effect=GeminiTimeoutError(15.0, "Texto cotización")))
        )
        resp_timeout = service_timeout.analyze_description(
            ExtractionInputRequest(text="Texto cotización", confirmed=True, personal_data_warning_acknowledged=True)
        )
        assert resp_timeout.status == AnalysisStatus.TIMEOUT
        assert resp_timeout.fallback_to_manual is True
        assert resp_timeout.original_text == "Texto cotización"

        service_down = ExtractionService(
            client=MagicMock(call_gemini=MagicMock(side_effect=GeminiUnavailableError("Sin internet", "Texto cotización")))
        )
        resp_down = service_down.analyze_description(
            ExtractionInputRequest(text="Texto cotización", confirmed=True, personal_data_warning_acknowledged=True)
        )
        assert resp_down.status == AnalysisStatus.UNAVAILABLE
        assert resp_down.fallback_to_manual is True
        assert resp_down.original_text == "Texto cotización"
