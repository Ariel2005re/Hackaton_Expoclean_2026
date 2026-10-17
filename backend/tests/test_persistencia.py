"""
Pruebas de persistencia para P1 (Tareas A09 / A10)
Cubre: RF-01 a RF-05, RF-12 a RF-17, RF-20 y RF-22.
"""

from app.models.config import PerfilRendimiento
from app.models.cotizacion import CotizacionBorrador


def test_editar_perfil_conserva_fuente_y_unidad(client, db_fresca):
    """
    RF-14, RF-16, RF-17: Permite editar el rendimiento de cálculo (m2_por_hora)
    sin perder ni alterar la fuente SERCOP ni la unidad original.
    """
    # 1. Crear perfil SERCOP de partida
    perfil = PerfilRendimiento(
        nombre="Limpieza General Oficinas",
        m2_por_hora=250.0,
        unidad="m2/hora",
        fuente="SERCOP",
        editable=True,
    )
    db_fresca.add(perfil)
    db_fresca.commit()
    db_fresca.refresh(perfil)
    perfil_id = perfil.id

    # 2. Actualizar únicamente el rendimiento a través de la API
    respuesta = client.put(
        f"/config/perfiles/{perfil_id}",
        json={"m2_por_hora": 285.5},
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["m2_por_hora"] == 285.5
    assert datos["fuente"] == "SERCOP"
    assert datos["unidad"] == "m2/hora"
    assert datos["nombre"] == "Limpieza General Oficinas"

    # 3. Confirmar persistencia en sesión independiente (db_fresca)
    perfil_guardado = (
        db_fresca.query(PerfilRendimiento)
        .filter(PerfilRendimiento.id == perfil_id)
        .first()
    )
    assert perfil_guardado is not None
    assert perfil_guardado.m2_por_hora == 285.5
    assert perfil_guardado.fuente == "SERCOP"
    assert perfil_guardado.unidad == "m2/hora"


def test_borrador_vacio_se_guarda_y_recupera(client, db_fresca):
    """
    RF-02, RF-13, RF-22: Un borrador sin cliente completo ni grupos
    debe poder guardarse y recuperarse exactamente.
    """
    cotizacion_id = "borr-test-vacio-001"
    payload = {
        "id": cotizacion_id,
        "cliente_id": None,
        "periodo": None,
        "grupos": [],
    }

    # Guardar borrador
    res_crear = client.post("/cotizaciones/", json=payload)
    assert res_crear.status_code == 200
    data_crear = res_crear.json()
    assert data_crear["id"] == cotizacion_id
    assert data_crear["estado"] == "borrador"
    assert data_crear["grupos"] == []

    # Reabrir borrador vía API
    res_get = client.get(f"/cotizaciones/{cotizacion_id}")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert data_get["id"] == cotizacion_id
    assert data_get["cliente_id"] is None
    assert data_get["grupos"] == []

    # Verificar en BD
    en_bd = (
        db_fresca.query(CotizacionBorrador)
        .filter(CotizacionBorrador.id == cotizacion_id)
        .first()
    )
    assert en_bd is not None
    assert en_bd.estado == "borrador"


def test_grupo_con_trabajos_y_recursos_se_recupera_exacto(client, db_fresca):
    """
    RF-01, RF-03, RF-04, RF-05, RF-12, RF-20, RF-22:
    Persistencia de cliente, cotización editable, grupos separados con
    trabajo general y especializado, y recursos propios y compartidos.
    """
    # 1. Crear cliente (RF-01)
    res_cli = client.post(
        "/clientes/",
        json={
            "tipo": "Empresa",
            "nombre": "Corporación Limpieza Total",
            "ruc": "1790011223001",
            "direccion": "Av. Amazonas y Colón",
            "telefono": "0991234567",
            "correo": "contacto@limpiezatotal.ec",
        },
    )
    assert res_cli.status_code == 200
    cliente_id = res_cli.json()["id"]

    # 2. Crear cotización con dos grupos distintos (RF-04, RF-05, RF-12, RF-20)
    cotizacion_id = "borr-test-full-002"
    payload = {
        "id": cotizacion_id,
        "cliente_id": cliente_id,
        "periodo": "Mensual",
        "grupos": [
            {
                "nombre": "Oficinas Administrativas",
                "cantidad": 8,
                "superficie_fisica": 280.0,
                "dias_semanales": 5,
                "visitas_diarias": 1,
                "estado_confirmacion": "manual",
                "trabajos": [
                    {
                        "tipo": "general",
                        "superficie_usada": 280.0,
                        "horas_estimadas": 4.5,
                        "personas": 2,
                    }
                ],
                "recursos": [
                    {
                        "tipo": "propio",
                        "id_insumo": 101,
                        "cantidad": 2.5,
                        "costo_unitario": 18.50,
                    }
                ],
            },
            {
                "nombre": "Vidrios de Fachada Exterior",
                "cantidad": 1,
                "superficie_fisica": 120.0,
                "dias_semanales": 2,
                "visitas_diarias": 1,
                "estado_confirmacion": "manual",
                "trabajos": [
                    {
                        "tipo": "especializado",
                        "superficie_usada": 75.0,  # Superficie propia de trabajo especializado (RF-12)
                        "horas_estimadas": 3.0,
                        "personas": 1,
                    }
                ],
                "recursos": [
                    {
                        "tipo": "compartido",
                        "id_insumo": 202,
                        "cantidad": 1.0,
                        "costo_unitario": 45.00,
                    }
                ],
            },
        ],
    }

    res_cot = client.post("/cotizaciones/", json=payload)
    assert res_cot.status_code == 200

    # 3. Validar recuperación exacta por GET
    res_recuperar = client.get(f"/cotizaciones/{cotizacion_id}")
    assert res_recuperar.status_code == 200
    rec = res_recuperar.json()
    assert rec["id"] == cotizacion_id
    assert rec["cliente_id"] == cliente_id
    assert rec["periodo"] == "Mensual"
    assert len(rec["grupos"]) == 2

    # Grupo 1 (General y recurso propio)
    g1 = next(g for g in rec["grupos"] if g["nombre"] == "Oficinas Administrativas")
    assert g1["cantidad"] == 8
    assert g1["superficie_fisica"] == 280.0
    assert len(g1["trabajos"]) == 1
    assert g1["trabajos"][0]["tipo"] == "general"
    assert g1["trabajos"][0]["superficie_usada"] == 280.0
    assert len(g1["recursos"]) == 1
    assert g1["recursos"][0]["tipo"] == "propio"
    assert g1["recursos"][0]["cantidad"] == 2.5

    # Grupo 2 (Especializado y recurso compartido)
    g2 = next(g for g in rec["grupos"] if g["nombre"] == "Vidrios de Fachada Exterior")
    assert g2["superficie_fisica"] == 120.0
    assert len(g2["trabajos"]) == 1
    assert g2["trabajos"][0]["tipo"] == "especializado"
    assert g2["trabajos"][0]["superficie_usada"] == 75.0
    assert len(g2["recursos"]) == 1
    assert g2["recursos"][0]["tipo"] == "compartido"
    assert g2["recursos"][0]["costo_unitario"] == 45.00