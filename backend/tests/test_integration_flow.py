"""PostgreSQL/API acceptance path for RF-01–RF-34 backend integration."""

from uuid import uuid4
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest

from backend.app.main import app
from backend.app.db.database import SessionLocal
from backend.app.models.cotizacion import CotizacionBorrador
from backend.app.models.config import Factor, PerfilRendimiento, Tarifa
from backend.app.models.ia_versiones import PropuestaIA, VersionCotizacion
from backend.app.routers.propuestas import get_service
from backend.app.extraction.models import (
    AnalysisStatus, AttributeCondition, AttributeProvenance,
    ExtractionServiceResponse, ProposedSpaceGroup,
)


def _cleanup(quote_id):
    with SessionLocal() as db:
        db.query(VersionCotizacion).filter_by(borrador_id=quote_id).delete()
        db.query(PropuestaIA).filter_by(cotizacion_id=quote_id).delete()
        db.query(CotizacionBorrador).filter_by(id=quote_id).delete()
        db.commit()


def _full_draft(quote_id):
    return {
        "id": quote_id,
        "client": {"name": "Cliente de prueba", "service_address": "Quito, Av. Ejemplo 10"},
        "service": {"infrastructure_type": "Oficinas", "cleaning_type": "Limpieza general",
                    "start_date": "2026-11-02", "period_type": "semanal",
                    "start_time": "08:00:00", "end_time": "16:00:00"},
        "groups": [{"group_id": "oficinas", "name": "Oficinas", "units_count": 2,
                    "sqm_per_unit": "50", "service_days": ["lunes", "miércoles"],
                    "visits_per_day": 1, "state": "bueno", "profile_id": "1",
                    "general_work": {"enabled": True, "productivity_sqm_per_hour": "50",
                                     "hourly_rate_usd": "10", "assigned_workers": 1}}],
        "resources": [{"resource_id": "r1", "description": "Insumo compartido",
                       "kind": "insumo", "scope": "compartido", "quantity": "0.5",
                       "unit_cost_usd": "2.00"}],
        "margin_percentage": "10", "discount_usd": "1", "tax_percentage": "15",
    }


def test_manual_draft_preview_issue_reuse_history_and_pdf():
    quote_id = f"it-{uuid4().hex}"
    client = TestClient(app)
    try:
        empty = client.post("/cotizaciones/", json={"id": quote_id})
        assert empty.status_code == 201, empty.text
        assert client.get(f"/cotizaciones/{quote_id}/preview").json()["is_emission_valid"] is False
        assert client.post(f"/cotizaciones/{quote_id}/versiones").status_code == 422

        draft = _full_draft(quote_id)
        assert client.put(f"/cotizaciones/{quote_id}", json=draft).status_code == 200
        assert client.get(f"/cotizaciones/{quote_id}").json()["groups"] == draft["groups"]
        preview = client.get(f"/cotizaciones/{quote_id}/preview")
        assert preview.status_code == 200, preview.text
        assert preview.json()["is_emission_valid"] is True, preview.json()
        assert preview.json()["calendar_summary"]["group_interventions"]["oficinas"] == 2
        assert preview.json()["calendar_summary"]["shared_service_days_count"] == 2

        first = client.post(f"/cotizaciones/{quote_id}/versiones")
        assert first.status_code == 200, first.text
        first = first.json()
        pdf = client.get(first["pdf_url"]).content
        assert pdf.startswith(b"%PDF-")
        pdf_text = " ".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
        assert first["code"] in pdf_text and "Cliente de prueba" in pdf_text
        assert "margen" not in pdf_text.lower() and "tarifa horaria" not in pdf_text.lower()
        assert client.post(f"/cotizaciones/{quote_id}/versiones").json() == first

        changed = _full_draft(quote_id)
        changed["groups"][0]["general_work"]["hourly_rate_usd"] = "12"
        client.put(f"/cotizaciones/{quote_id}", json=changed)
        second = client.post(f"/cotizaciones/{quote_id}/versiones")
        assert second.status_code == 200, second.text
        assert second.json()["code"] != first["code"]
        client.put(f"/cotizaciones/{quote_id}", json=draft)
        assert client.post(f"/cotizaciones/{quote_id}/versiones").json() == first
        assert len(client.get("/historial", params={"query": "Cliente de prueba"}).json()) >= 2
    finally:
        _cleanup(quote_id)


class FakeExtraction:
    def analyze_description(self, request):
        group = ProposedSpaceGroup(
            id="proposal-1", name="Aulas", quantity=2, unit_area_m2=40,
            source_fragment="2 aulas de 40 m2", can_be_confirmed=True,
            attributes={
                "name": AttributeProvenance(value="Aulas", condition=AttributeCondition.EXPLICIT,
                                            source_fragment="aulas"),
                "quantity": AttributeProvenance(value=2, condition=AttributeCondition.EXPLICIT,
                                                source_fragment="2 aulas"),
                "unit_area_m2": AttributeProvenance(value=40, condition=AttributeCondition.EXPLICIT,
                                                    source_fragment="40 m2"),
            },
        )
        return ExtractionServiceResponse(
            status=AnalysisStatus.SUCCESS, original_text=request.text,
            revisable_groups=[group], message="Revisar propuesta",
        )


def test_assisted_review_persists_separately_and_manual_draft_survives():
    quote_id = f"it-{uuid4().hex}"
    client = TestClient(app)
    app.dependency_overrides[get_service] = lambda: FakeExtraction()
    try:
        assert client.post("/cotizaciones/", json={"id": quote_id}).status_code == 201
        payload = {"text": "2 aulas de 40 m2", "confirmed": True,
                   "personal_data_warning_acknowledged": True}
        analyzed = client.post(f"/cotizaciones/{quote_id}/propuestas/analizar", json=payload)
        assert analyzed.status_code == 200, analyzed.text
        proposal_id = analyzed.json()["id"]
        assert client.get(f"/cotizaciones/{quote_id}").json()["groups"] == []
        reviewed = client.post(
            f"/cotizaciones/{quote_id}/propuestas/{proposal_id}/confirmar",
            json={"group_id": "proposal-1"},
        )
        assert reviewed.status_code == 200, reviewed.text
        groups = client.get(f"/cotizaciones/{quote_id}").json()["groups"]
        assert len(groups) == 1 and groups[0]["provenance"]["quantity"]["source_fragment"] == "2 aulas"
        assert client.get(f"/cotizaciones/{quote_id}/preview").json()["is_emission_valid"] is False
        client.post(f"/cotizaciones/{quote_id}/propuestas/analizar", json=payload)
        assert len(client.get(f"/cotizaciones/{quote_id}").json()["groups"]) == 1
    finally:
        app.dependency_overrides.clear()
        _cleanup(quote_id)


def test_drafts_and_latest_review_can_be_reopened_without_browser_state():
    """RF-06, RF-09, RF-22, RF-28: fresh clients recover persisted state."""
    quote_id = f"it-{uuid4().hex}"
    other_id = f"it-{uuid4().hex}"
    client = TestClient(app)
    app.dependency_overrides[get_service] = lambda: FakeExtraction()
    try:
        for identifier in (quote_id, other_id):
            assert client.post("/cotizaciones/", json={"id": identifier}).status_code == 201
        assert client.get(f"/cotizaciones/{quote_id}/propuestas/actual").status_code == 204
        assert client.get("/cotizaciones/inexistente/propuestas/actual").status_code == 404
        payload = {"text": "2 aulas de 40 m2", "confirmed": True,
                   "personal_data_warning_acknowledged": True}
        first = client.post(f"/cotizaciones/{quote_id}/propuestas/analizar", json=payload).json()
        corrected = client.post(f"/cotizaciones/{quote_id}/propuestas/{first['id']}/corregir",
                                json={"group_id": "proposal-1", "attribute_name": "unit_area_m2", "new_value": 45})
        assert corrected.status_code == 200, corrected.text
        fresh = TestClient(app)
        assert quote_id in {d["id"] for d in fresh.get("/cotizaciones/").json()}
        restored = fresh.get(f"/cotizaciones/{quote_id}/propuestas/actual").json()
        assert restored["review"]["revisable_groups"][0]["unit_area_m2"] == 45
        assert restored["review"]["original_text"] == payload["text"]
        assert fresh.get(f"/cotizaciones/{other_id}/propuestas/actual").status_code == 204
        second = client.post(f"/cotizaciones/{quote_id}/propuestas/analizar", json=payload).json()
        assert second["id"] != first["id"]
        assert fresh.get(f"/cotizaciones/{quote_id}/propuestas/actual").json()["id"] == second["id"]
        assert fresh.get(f"/cotizaciones/{quote_id}").json()["groups"] == []
    finally:
        app.dependency_overrides.clear()
        _cleanup(quote_id)
        _cleanup(other_id)


def test_sercop_profiles_keep_original_units_and_no_automatic_rate():
    client = TestClient(app)
    profiles = client.get("/config/perfiles").json()
    assert {p["nombre"] for p in profiles[:4]} == {
        "Oficinas", "Campamentos", "Instituciones educativas", "Áreas externas",
    }
    assert all(p["fuente_url"].startswith("https://portal.compraspublicas.gob.ec/")
               and p["valor_original"] is not None and p["unidad_original"]
               and p["m2_por_hora"] is None for p in profiles[:4])
    assert [f["valor"] for f in client.get("/config/factores").json()[:3]] == [1.0, 1.25, 1.5]


class FailedExtraction:
    def analyze_description(self, request):
        return ExtractionServiceResponse(
            status=AnalysisStatus.UNAVAILABLE, original_text=request.text,
            fallback_to_manual=True, message="Gemini no disponible",
        )


def test_gemini_failure_preserves_text_and_empty_manual_draft():
    quote_id = f"it-{uuid4().hex}"
    client = TestClient(app)
    app.dependency_overrides[get_service] = lambda: FailedExtraction()
    try:
        client.post("/cotizaciones/", json={"id": quote_id})
        result = client.post(f"/cotizaciones/{quote_id}/propuestas/analizar",
                             json={"text": "aulas", "confirmed": True,
                                   "personal_data_warning_acknowledged": True})
        assert result.status_code == 200, result.text
        assert result.json()["analysis"]["status"] == "UNAVAILABLE"
        assert result.json()["review"]["original_text"] == "aulas"
        assert client.get(f"/cotizaciones/{quote_id}").json()["groups"] == []
        assert client.put(f"/cotizaciones/{quote_id}", json=_full_draft(quote_id)).status_code == 200
        assert client.get(f"/cotizaciones/{quote_id}/preview").json()["is_emission_valid"] is True
    finally:
        app.dependency_overrides.clear()
        _cleanup(quote_id)


@pytest.mark.parametrize("failure", ["render", "persist"])
def test_pdf_failures_leave_no_version_and_keep_draft(monkeypatch, failure):
    """RF-26/RF-34: HTTP failure rolls back actual PostgreSQL writes."""
    from backend.app.routers import versiones
    from backend.app.documents.issuance import EmissionService
    from backend.app.version_store import PostgresVersionTransaction

    quote_id = f"it-{uuid4().hex}"
    client = TestClient(app, raise_server_exceptions=False)
    try:
        assert client.post("/cotizaciones/", json=_full_draft(quote_id)).status_code == 201
        before = client.get(f"/cotizaciones/{quote_id}").json()
        if failure == "render":
            def fail_render(snapshot):
                raise RuntimeError("Fallo de generación simulado")
            monkeypatch.setattr(versiones, "EmissionService",
                                lambda store: EmissionService(store, render_pdf=fail_render))
        else:
            def fail_commit(transaction):
                transaction.db.flush()  # A real INSERT must be undone, not just an in-memory stage.
                raise RuntimeError("Fallo de persistencia simulado")
            monkeypatch.setattr(PostgresVersionTransaction, "commit", fail_commit)
        assert client.post(f"/cotizaciones/{quote_id}/versiones").status_code == 500
        assert client.get(f"/cotizaciones/{quote_id}").json() == before
        with SessionLocal() as db:
            assert db.query(VersionCotizacion).filter_by(borrador_id=quote_id).count() == 0
        monkeypatch.undo()
        retry = client.post(f"/cotizaciones/{quote_id}/versiones")
        assert retry.status_code == 200, retry.text
        assert client.get(retry.json()["pdf_url"]).content.startswith(b"%PDF-")
    finally:
        _cleanup(quote_id)


def test_editable_company_assumptions_feed_preview_without_changing_draft():
    quote_id = f"it-{uuid4().hex}"
    client = TestClient(app)
    with SessionLocal() as db:
        profile = db.query(PerfilRendimiento).filter_by(nombre="Oficinas").one()
        factor = db.query(Factor).filter_by(nombre="bueno").one()
        rate = db.query(Tarifa).filter_by(descripcion="Personal general").one()
        original = (profile.m2_por_hora, factor.valor, rate.monto)
        ids = profile.id, factor.id, rate.id
    try:
        draft = _full_draft(quote_id)
        work = draft["groups"][0]["general_work"]
        work.pop("productivity_sqm_per_hour")
        work.pop("hourly_rate_usd")
        draft["groups"][0]["profile_id"] = str(ids[0])
        assert client.post("/cotizaciones/", json=draft).status_code == 201
        assert not client.get(f"/cotizaciones/{quote_id}/preview").json()["is_emission_valid"]
        assert client.put(f"/config/perfiles/{ids[0]}", json={"m2_por_hora": 50}).status_code == 200
        assert client.put(f"/config/tarifas/{ids[2]}", json={"valor": 10}).status_code == 200
        assert client.put(f"/config/factores/{ids[1]}", json={"valor": 1.25}).status_code == 200
        preview = client.get(f"/cotizaciones/{quote_id}/preview").json()
        assert preview["is_emission_valid"], preview
        assert client.get(f"/cotizaciones/{quote_id}").json()["groups"][0]["general_work"] == work
    finally:
        _cleanup(quote_id)
        with SessionLocal() as db:
            db.get(PerfilRendimiento, ids[0]).m2_por_hora = original[0]
            db.get(Factor, ids[1]).valor = original[1]
            db.get(Tarifa, ids[2]).monto = original[2]
            db.commit()
