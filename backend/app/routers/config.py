from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.config import PerfilRendimiento
from app.schemas import PerfilResponse

router = APIRouter(prefix="/config", tags=["Configuración"])

@router.get("/perfiles", response_model=list[PerfilResponse])
def obtener_perfiles(db: Session = Depends(get_db)):
    return db.query(PerfilRendimiento).all()