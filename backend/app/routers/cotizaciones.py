from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.models.cotizacion import CotizacionBorrador, Grupo, Trabajo, Recurso
from app.schemas import CotizacionCreate, CotizacionResponse

router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones"])


@router.post("/", response_model=CotizacionResponse)
def crear_borrador(cotizacion: CotizacionCreate, db: Session = Depends(get_db)):
    # 1. Crear el borrador base
    db_cotizacion = CotizacionBorrador(
        id=cotizacion.id,
        cliente_id=cotizacion.cliente_id,
        periodo=cotizacion.periodo,
    )
    db.add(db_cotizacion)

  
    if cotizacion.grupos:
        for g in cotizacion.grupos:
            datos_grupo = g.model_dump(exclude={"trabajos", "recursos"})
            nuevo_grupo = Grupo(**datos_grupo, cotizacion_id=cotizacion.id)
            db.add(nuevo_grupo)
            db.flush()  # para obtener nuevo_grupo.id antes del commit

            for t in g.trabajos or []:
                db.add(Trabajo(**t.model_dump(), grupo_id=nuevo_grupo.id))

            for r in g.recursos or []:
                db.add(Recurso(**r.model_dump(), grupo_id=nuevo_grupo.id))

    db.commit()
    return obtener_borrador(cotizacion.id, db)


@router.get("/{cotizacion_id}", response_model=CotizacionResponse)
def obtener_borrador(cotizacion_id: str, db: Session = Depends(get_db)):
    # Reabrir un borrador debe reproducir exactamente los valores guardados
    # (tasks.md A08/A09), incluyendo grupos, trabajos y recursos.
    db_cotizacion = (
        db.query(CotizacionBorrador)
        .options(
            joinedload(CotizacionBorrador.grupos).joinedload(Grupo.trabajos),
            joinedload(CotizacionBorrador.grupos).joinedload(Grupo.recursos),
        )
        .filter(CotizacionBorrador.id == cotizacion_id)
        .first()
    )
    if db_cotizacion is None:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    return db_cotizacion