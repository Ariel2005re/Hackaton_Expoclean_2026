"""Customer and profile schemas; quote drafts use DraftPayload in the router."""

from pydantic import BaseModel, ConfigDict


class PerfilResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    m2_por_hora: float | None
    unidad: str | None
    fuente: str
    valor_original: float | None = None
    unidad_original: str | None = None
    fuente_url: str | None = None
    es_ejemplo: bool = True


class PerfilUpdate(BaseModel):
    m2_por_hora: float | None = None


class ClienteBase(BaseModel):
    tipo: str | None = None
    nombre: str | None = None
    ruc: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    correo: str | None = None


class ClienteCreate(ClienteBase):
    pass


class ClienteResponse(ClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
