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


class PerfilUpdate(BaseModel):
    # Solo se permite editar el valor de rendimiento. Nombre, unidad y fuente
    # se conservan intactos para no perder la referencia SERCOP original
    # (ver constitution.md punto 8 y tasks.md A09).
    m2_por_hora: float


class ClienteBase(BaseModel):
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    ruc: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteResponse(ClienteBase):
    id: int

    class Config:
        from_attributes = True


class TrabajoCreate(BaseModel):
    tipo: str  # "general" o "especializado"
    superficie_usada: Optional[float] = None
    horas_estimadas: Optional[float] = None
    personas: Optional[int] = None


class TrabajoResponse(TrabajoCreate):
    id: int

    class Config:
        from_attributes = True


class RecursoCreate(BaseModel):
    tipo: str  # "propio" o "compartido"
    id_insumo: Optional[int] = None
    cantidad: Optional[float] = None
    costo_unitario: Optional[float] = None


class RecursoResponse(RecursoCreate):
    id: int

    class Config:
        from_attributes = True


class GrupoCreate(BaseModel):
    nombre: Optional[str] = None
    cantidad: int = 1
    superficie_fisica: Optional[float] = None
    dias_semanales: Optional[int] = None
    visitas_diarias: Optional[int] = None
    estado_confirmacion: Optional[str] = "manual"
    trabajos: Optional[List[TrabajoCreate]] = []
    recursos: Optional[List[RecursoCreate]] = []


class GrupoResponse(BaseModel):
    id: int
    nombre: Optional[str] = None
    cantidad: int
    superficie_fisica: Optional[float] = None
    dias_semanales: Optional[int] = None
    visitas_diarias: Optional[int] = None
    estado_confirmacion: str
    trabajos: List[TrabajoResponse] = []
    recursos: List[RecursoResponse] = []

    class Config:
        from_attributes = True


class CotizacionCreate(BaseModel):
    id: str
    cliente_id: Optional[int] = None
    periodo: Optional[str] = None
    grupos: Optional[List[GrupoCreate]] = []


class CotizacionResponse(BaseModel):
    id: str
    cliente_id: Optional[int] = None
    periodo: Optional[str] = None
    estado: str
    grupos: List[GrupoResponse] = []

    class Config:
        from_attributes = True