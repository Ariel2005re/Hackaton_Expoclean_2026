"""Unit and API tests for ExtractionService contract and distinguishable statuses (Task C06 · RF-06, RF-09–RF-11, RF-29–RF-31)."""

import json
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.extraction.client import GeminiExtractionClient
from backend.app.extraction.exceptions import (
    GeminiError,
    GeminiQuotaExceededError,
    GeminiRejectionError,
    GeminiTimeoutError,
    GeminiUnavailableError,
)
from backend.app.extraction.group_validator import validate_proposed_group
from backend.app.extraction.models import (
    AnalysisStatus,
    ExtractionInputRequest,
    ProposedSpaceGroup,
)
from backend.app.extraction.router import extraction_router
from backend.app.extraction.service import ExtractionService


def create_confirmed_group(name: str) -> ProposedSpaceGroup:
    raw = {
        "name": name,
        "quantity": 5,
        "unit_area_m2": 30.0,
        "source_fragment": f"espacio confirmado: {name}",
    }
    g, _ = validate_proposed_group(raw)
    assert g is not None
    return g


class TestDistinguishableStatusesAndPreservation:
    """Verifies that success, partial, rejection, and timeout deliver distinct statuses without altering confirmed groups (C06)."""

    def test_model_rejection_preserves_text_and_exposes_only_error_code(self):
        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.side_effect = GeminiError(message="detalle privado", code="GEMINI_HTTP_404")
        response = ExtractionService(client=mock_client).analyze_description(ExtractionInputRequest(
            text="Dos oficinas", confirmed=True, personal_data_warning_acknowledged=True))
        assert response.error_code == "GEMINI_HTTP_404"
        assert response.original_text == "Dos oficinas"
        assert response.fallback_to_manual
        assert "detalle privado" not in response.message

    def test_status_success_preserves_confirmed_groups(self):
        existing_confirmed = [create_confirmed_group("oficinas planta baja")]
        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.return_value = {
            "spaces": [
                {
                    "name": "aulas",
                    "quantity": 4,
                    "unit_area_m2": 45.0,
                    "source_fragment": "4 aulas de 45 m²",
                }
            ]
        }

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text="4 aulas de 45 m²",
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        resp = service.analyze_description(req, existing_confirmed_groups=existing_confirmed)

        assert resp.status == AnalysisStatus.SUCCESS
        assert resp.fallback_to_manual is False
        assert len(resp.revisable_groups) == 1
        assert resp.revisable_groups[0].name == "aulas"
        # Confirmed groups untouched (RF-10)
        assert len(resp.confirmed_groups) == 1
        assert resp.confirmed_groups[0].name == "oficinas planta baja"
        assert resp.original_text == "4 aulas de 45 m²"

    def test_status_partial_success_preserves_confirmed_groups(self):
        existing_confirmed = [create_confirmed_group("oficinas")]
        mock_client = MagicMock(spec=GeminiExtractionClient)
        # Returns 1 valid group and 1 defective group (missing name)
        mock_client.call_gemini.return_value = {
            "spaces": [
                {
                    "name": "bodega",
                    "quantity": 1,
                    "unit_area_m2": 25.0,
                    "source_fragment": "1 bodega de 25 m²",
                },
                {
                    "quantity": 2,  # Defective: missing name
                    "source_fragment": "2 espacios sin nombre",
                },
            ]
        }

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text="1 bodega de 25 m² y 2 espacios sin nombre",
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        resp = service.analyze_description(req, existing_confirmed_groups=existing_confirmed)

        assert resp.status == AnalysisStatus.PARTIAL_SUCCESS
        assert resp.fallback_to_manual is False
        assert len(resp.revisable_groups) == 1
        assert len(resp.defective_groups) == 1
        assert len(resp.confirmed_groups) == 1
        assert resp.confirmed_groups[0].name == "oficinas"

    def test_status_rejected_on_safety_block_preserves_text_and_confirmed(self):
        existing_confirmed = [create_confirmed_group("oficinas")]
        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.side_effect = GeminiRejectionError(
            reason="Bloqueo por filtros de seguridad",
            original_text="Texto bloqueado",
        )

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text="Texto bloqueado",
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        resp = service.analyze_description(req, existing_confirmed_groups=existing_confirmed)

        assert resp.status == AnalysisStatus.REJECTED
        assert resp.fallback_to_manual is True
        assert resp.original_text == "Texto bloqueado"
        assert len(resp.confirmed_groups) == 1
        assert resp.confirmed_groups[0].name == "oficinas"

    def test_status_timeout_preserves_text_and_confirmed(self):
        existing_confirmed = [create_confirmed_group("oficinas")]
        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.side_effect = GeminiTimeoutError(
            timeout_seconds=20.0,
            original_text="Texto largo con demora",
        )

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text="Texto largo con demora",
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        resp = service.analyze_description(req, existing_confirmed_groups=existing_confirmed)

        assert resp.status == AnalysisStatus.TIMEOUT
        assert resp.fallback_to_manual is True
        assert resp.original_text == "Texto largo con demora"
        assert len(resp.confirmed_groups) == 1

    def test_status_unavailable_preserves_text_and_confirmed(self):
        existing_confirmed = [create_confirmed_group("oficinas")]
        mock_client = MagicMock(spec=GeminiExtractionClient)
        mock_client.call_gemini.side_effect = GeminiUnavailableError(
            detail="Fallo de conexión DNS",
            original_text="Texto en borrador",
        )

        service = ExtractionService(client=mock_client)
        req = ExtractionInputRequest(
            text="Texto en borrador",
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        resp = service.analyze_description(req, existing_confirmed_groups=existing_confirmed)

        assert resp.status == AnalysisStatus.UNAVAILABLE
        assert resp.fallback_to_manual is True
        assert resp.original_text == "Texto en borrador"
        assert len(resp.confirmed_groups) == 1


class TestFastApiExtractionRouter:
    """Verifies HTTP API integration via FastAPI router."""

    def test_validate_text_endpoint(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(extraction_router)
        client = TestClient(app)

        # Valid text
        resp = client.post("/extraction/validate-text", json={"text": "Limpieza de 5 aulas"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["code_point_count"] == len("Limpieza de 5 aulas")

        # Blank text
        resp_blank = client.post("/extraction/validate-text", json={"text": "   \n\t  "})
        assert resp_blank.status_code == 200
        data_blank = resp_blank.json()
        assert data_blank["is_valid"] is False
        assert data_blank["error_code"] == "BLANK_TEXT"

    def test_analyze_endpoint_requires_confirmation(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(extraction_router)
        client = TestClient(app)

        unconfirmed_payload = {
            "text": "8 oficinas de 35 m²",
            "confirmed": False,
        }
        resp = client.post("/extraction/analyze", json=unconfirmed_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert data["fallback_to_manual"] is True
        assert data["error_code"] == "CONFIRMATION_REQUIRED"
