"""Editable company assumptions and SERCOP reference profiles (RF-14–RF-17)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.models.config import EmpresaConfig, Factor, Tarifa, PerfilRendimiento, PlantillaRecurso
from backend.app.schemas import PerfilResponse, PerfilUpdate

router = APIRouter(prefix="/config", tags=["Configuración"])


class OwnProfile(BaseModel):
    nombre: str
    m2_por_hora: float | None = None


class NumberUpdate(BaseModel):
    valor: float = Field(ge=0)


class CompanyUpdate(BaseModel):
    nombre: str
    margen_porcentaje: float = Field(ge=0)
    impuesto_porcentaje: float = Field(ge=0)


class TemplatePayload(BaseModel):
    nombre: str
    tipo: str
    unidad: str
    costo_unitario: float = Field(ge=0)


@router.post("/plantillas", status_code=201)
def create_template(payload: TemplatePayload, db: Session = Depends(get_db)):
    row = PlantillaRecurso(**payload.model_dump(), fuente="Propia")
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, **payload.model_dump(), "fuente": row.fuente}


@router.put("/plantillas/{template_id}")
def edit_template(template_id: int, payload: TemplatePayload, db: Session = Depends(get_db)):
    row = db.get(PlantillaRecurso, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return {"id": row.id, **payload.model_dump(), "fuente": row.fuente}


@router.get("/empresa")
def get_company(db: Session = Depends(get_db)):
    row = db.query(EmpresaConfig).first()
    return {"nombre": row.nombre, "margen_porcentaje": row.margen_porcentaje,
            "impuesto_porcentaje": row.impuesto_porcentaje} if row else None


@router.put("/empresa")
def edit_company(payload: CompanyUpdate, db: Session = Depends(get_db)):
    row = db.query(EmpresaConfig).first()
    if row is None:
        row = EmpresaConfig()
        db.add(row)
    row.nombre = payload.nombre
    row.margen_porcentaje = payload.margen_porcentaje
    row.impuesto_porcentaje = payload.impuesto_porcentaje
    db.commit()
    return get_company(db)


@router.get("/perfiles", response_model=list[PerfilResponse])
def list_profiles(db: Session = Depends(get_db)):
    return db.query(PerfilRendimiento).order_by(PerfilRendimiento.id).all()


@router.post("/perfiles", response_model=PerfilResponse, status_code=201)
def create_profile(payload: OwnProfile, db: Session = Depends(get_db)):
    if not payload.nombre.strip():
        raise HTTPException(status_code=422, detail="El perfil requiere nombre")
    if payload.m2_por_hora is not None and payload.m2_por_hora <= 0:
        raise HTTPException(status_code=422, detail="El rendimiento debe ser positivo")
    profile = PerfilRendimiento(nombre=payload.nombre, m2_por_hora=payload.m2_por_hora,
                                unidad="m²/hora de trabajo", fuente="Propio", editable=True,
                                es_ejemplo=False)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/perfiles/{perfil_id}", response_model=PerfilResponse)
def edit_profile(perfil_id: int, payload: PerfilUpdate, db: Session = Depends(get_db)):
    profile = db.get(PerfilRendimiento, perfil_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    if payload.m2_por_hora is not None and payload.m2_por_hora <= 0:
        raise HTTPException(status_code=422, detail="El rendimiento debe ser positivo")
    profile.m2_por_hora = payload.m2_por_hora
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/factores")
def list_factors(db: Session = Depends(get_db)):
    return [{"id": f.id, "nombre": f.nombre, "valor": f.valor, "es_ejemplo": True}
            for f in db.query(Factor).order_by(Factor.id)]


@router.put("/factores/{factor_id}")
def edit_factor(factor_id: int, payload: NumberUpdate, db: Session = Depends(get_db)):
    row = db.get(Factor, factor_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Factor no encontrado")
    if payload.valor <= 0:
        raise HTTPException(status_code=422, detail="El factor debe ser positivo")
    row.valor = payload.valor
    db.commit()
    return {"id": row.id, "nombre": row.nombre, "valor": row.valor}


@router.get("/tarifas")
def list_rates(db: Session = Depends(get_db)):
    return [{"id": r.id, "descripcion": r.descripcion, "monto": r.monto,
             "unidad": r.unidad, "es_ejemplo": r.es_ejemplo}
            for r in db.query(Tarifa).order_by(Tarifa.id)]


@router.put("/tarifas/{rate_id}")
def edit_rate(rate_id: int, payload: NumberUpdate, db: Session = Depends(get_db)):
    row = db.get(Tarifa, rate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    if payload.valor <= 0:
        raise HTTPException(status_code=422, detail="La tarifa debe ser positiva")
    row.monto = payload.valor
    row.es_ejemplo = False
    db.commit()
    return {"id": row.id, "descripcion": row.descripcion, "monto": row.monto,
            "unidad": row.unidad, "es_ejemplo": row.es_ejemplo}


@router.get("/plantillas")
def list_templates(db: Session = Depends(get_db)):
    return [{"id": r.id, "nombre": r.nombre, "tipo": r.tipo, "unidad": r.unidad,
             "costo_unitario": r.costo_unitario, "fuente": r.fuente}
            for r in db.query(PlantillaRecurso).order_by(PlantillaRecurso.id)]
