from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.config import PerfilRendimiento
from app.schemas import PerfilResponse, PerfilUpdate

router = APIRouter(prefix="/config", tags=["Configuración"])


@router.get("/perfiles", response_model=list[PerfilResponse])
def obtener_perfiles(db: Session = Depends(get_db)):
    return db.query(PerfilRendimiento).all()


@router.put("/perfiles/{perfil_id}", response_model=PerfilResponse)
def editar_perfil(perfil_id: int, cambios: PerfilUpdate, db: Session = Depends(get_db)):
   
    db_perfil = (
        db.query(PerfilRendimiento)
        .filter(PerfilRendimiento.id == perfil_id)
        .first()
    )
    if db_perfil is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    db_perfil.m2_por_hora = cambios.m2_por_hora
    db.commit()
    db.refresh(db_perfil)
    return db_perfil