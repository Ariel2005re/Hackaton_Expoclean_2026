from pydantic import BaseModel
from typing import Optional, List

class PerfilResponse(BaseModel):
    id: int
    nombre: str
    m2_por_hora: float
    unidad: str
    fuente: str
    class Config:
        from_attributes = True

class ClienteBase(BaseModel):
    nombre: Optional[str] = None
    ruc: Optional[str] = None
    correo: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(ClienteBase):
    id: int
    class Config:
        from_attributes = True

class GrupoCreate(BaseModel):
    nombre: Optional[str] = None
    cantidad: int = 1
    superficie_fisica: Optional[float] = None
    
class CotizacionCreate(BaseModel):
    id: str
    cliente_id: Optional[int] = None
    periodo: Optional[str] = None
    grupos: Optional[List[GrupoCreate]] = []