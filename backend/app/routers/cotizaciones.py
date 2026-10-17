from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.cotizacion import CotizacionBorrador, Grupo
from app.schemas import CotizacionCreate

router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones"])

@router.post("/")
def crear_borrador(cotizacion: CotizacionCreate, db: Session = Depends(get_db)):
    # 1. Crear el borrador base
    db_cotizacion = CotizacionBorrador(
        id=cotizacion.id,
        cliente_id=cotizacion.cliente_id,
        periodo=cotizacion.periodo
    )
    db.add(db_cotizacion)
    
    # 2. Agregar los grupos si el borrador los incluye
    if cotizacion.grupos:
        for g in cotizacion.grupos:
            nuevo_grupo = Grupo(**g.model_dump(), cotizacion_id=cotizacion.id)
            db.add(nuevo_grupo)
            
    db.commit()
    return {"mensaje": "Borrador guardado exitosamente", "id": cotizacion.id}