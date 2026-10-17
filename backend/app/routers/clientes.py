from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.models.cotizacion import Cliente
from app.schemas import ClienteCreate, ClienteResponse

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteResponse)
def crear_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    db_cliente = Cliente(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


@router.get("/", response_model=list[ClienteResponse])
def buscar_clientes(
    ruc: Optional[str] = None,
    nombre: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Cliente)
    if ruc:
        query = query.filter(Cliente.ruc == ruc)
    if nombre:
        query = query.filter(Cliente.nombre.ilike(f"%{nombre}%"))
    return query.all()


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    db_cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if db_cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return db_cliente