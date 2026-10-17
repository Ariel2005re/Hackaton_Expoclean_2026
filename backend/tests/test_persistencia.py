"""P1 A09/A10 scenarios adapted to the integrated RF-01–RF-22 contract."""

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.db.database import SessionLocal
from backend.app.main import app
from backend.app.models.config import PerfilRendimiento
from backend.app.models.cotizacion import Cliente, CotizacionBorrador


def test_editar_rendimiento_conserva_referencia_sercop():
    """RF-14–RF-17: a calculation value does not overwrite its source."""
    client = TestClient(app)
    with SessionLocal() as db:
        profile = db.query(PerfilRendimiento).filter_by(nombre="Oficinas").one()
        profile_id = profile.id
        original = (profile.m2_por_hora, profile.valor_original,
                    profile.unidad_original, profile.fuente_url)
    try:
        response = client.put(f"/config/perfiles/{profile_id}",
                              json={"m2_por_hora": 285.5})
        assert response.status_code == 200, response.text
        with SessionLocal() as db:
            saved = db.get(PerfilRendimiento, profile_id)
            assert saved.m2_por_hora == 285.5
            assert (saved.valor_original, saved.unidad_original, saved.fuente_url) == original[1:]
    finally:
        with SessionLocal() as db:
            db.get(PerfilRendimiento, profile_id).m2_por_hora = original[0]
            db.commit()


def test_borrador_vacio_persiste_y_no_emite():
    """RF-02, RF-13, RF-22: preserve incomplete work with visible issues."""
    quote_id = f"p1-{uuid4().hex}"
    client = TestClient(app)
    try:
        response = client.post("/cotizaciones/", json={"id": quote_id})
        assert response.status_code == 201, response.text
        assert client.get(f"/cotizaciones/{quote_id}").json()["groups"] == []
        with SessionLocal() as db:
            saved = db.get(CotizacionBorrador, quote_id)
            assert saved is not None and saved.datos["groups"] == []
        preview = client.get(f"/cotizaciones/{quote_id}/preview").json()
        assert not preview["is_emission_valid"] and preview["pending_emission_issues"]
        assert client.post(f"/cotizaciones/{quote_id}/versiones").status_code == 422
    finally:
        with SessionLocal() as db:
            db.query(CotizacionBorrador).filter_by(id=quote_id).delete()
            db.commit()


def test_cliente_dos_trabajos_y_recursos_propios_compartidos_persisten():
    """RF-01, RF-04–RF-05, RF-12, RF-20, RF-22: round trip of full draft."""
    quote_id = f"p1-{uuid4().hex}"
    client = TestClient(app)
    customer_id = None
    try:
        created = client.post("/clientes/", json={"nombre": "Corporación Limpieza Total",
                                                  "ruc": "1790011223001"})
        assert created.status_code == 200, created.text
        customer_id = created.json()["id"]
        profile_id = client.get("/config/perfiles").json()[0]["id"]
        draft = {
            "id": quote_id, "cliente_id": customer_id,
            "client": {"service_address": "Av. Amazonas y Colón"},
            "service": {"start_date": "2026-11-02", "period_type": "semanal",
                        "start_time": "08:00:00", "end_time": "17:00:00"},
            "groups": [
                {"group_id": "oficinas", "name": "Oficinas Administrativas",
                 "units_count": 8, "sqm_per_unit": "35", "service_days": ["lunes", "miércoles"],
                 "visits_per_day": 1, "state": "bueno", "profile_id": str(profile_id),
                 "general_work": {"enabled": True, "productivity_sqm_per_hour": "70",
                                  "hourly_rate_usd": "10", "assigned_workers": 2}},
                {"group_id": "fachada", "name": "Vidrios de Fachada Exterior",
                 "units_count": 1, "sqm_per_unit": "120", "service_days": ["martes"],
                 "visits_per_day": 1, "state": "regular", "profile_id": str(profile_id),
                 "specialized_work": {"enabled": True, "custom_surface_sqm": "75",
                                      "productivity_sqm_per_hour": "25",
                                      "hourly_rate_usd": "15", "assigned_workers": 1}},
            ],
            "resources": [
                {"resource_id": "r-own", "description": "Detergente", "kind": "insumo",
                 "scope": "grupo", "group_id": "oficinas", "quantity": "2.5",
                 "unit_cost_usd": "18.50"},
                {"resource_id": "r-shared", "description": "Herramienta", "kind": "herramienta",
                 "scope": "compartido", "quantity": "1", "unit_cost_usd": "45"},
            ],
        }
        response = client.post("/cotizaciones/", json=draft)
        assert response.status_code == 201, response.text
        reopened = client.get(f"/cotizaciones/{quote_id}").json()
        assert reopened["groups"] == draft["groups"]
        assert reopened["resources"] == draft["resources"]
        with SessionLocal() as db:
            saved = db.get(CotizacionBorrador, quote_id)
            assert saved.datos["groups"] == draft["groups"]
        preview = client.get(f"/cotizaciones/{quote_id}/preview").json()
        assert preview["is_emission_valid"], preview
        assert preview["calendar_summary"]["shared_service_days_count"] == 3
        assert len(preview["pricing_summary"]["group_resource_lines"]) == 1
        assert len(preview["pricing_summary"]["shared_resource_lines"]) == 1
    finally:
        with SessionLocal() as db:
            db.query(CotizacionBorrador).filter_by(id=quote_id).delete()
            if customer_id:
                db.query(Cliente).filter_by(id=customer_id).delete()
            db.commit()
