from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, LargeBinary, Numeric, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class PropuestaIA(Base):
    __tablename__ = "propuestas_ia"
    id = Column(Integer, primary_key=True, index=True)
    cotizacion_id = Column(String, ForeignKey("cotizaciones_borrador.id"))
    texto_original = Column(String, nullable=False) # El texto que pegó el usuario
    estado = Column(String, default="revisable") # revisable, confirmada, rechazada
    datos_extraidos = Column(JSON, nullable=True) # El JSON crudo que devolvió Gemini
    estado_revision = Column(JSON, nullable=True)
    
    cotizacion = relationship("CotizacionBorrador")

class VersionCotizacion(Base):
    __tablename__ = "versiones_cotizacion"
    __table_args__ = (UniqueConstraint("borrador_id", "identidad", name="uq_version_identidad"),)
    id = Column(String, primary_key=True, index=True) # Ej: "VER-1234-A"
    borrador_id = Column(String, ForeignKey("cotizaciones_borrador.id"))
    fecha_emision = Column(DateTime(timezone=True), server_default=func.now())
    pdf_url = Column(String, nullable=True) # Compatibilidad con el contrato anterior
    pdf = Column(LargeBinary, nullable=False)
    identidad = Column(String(64), nullable=False)
    
    # Datos inmutables: Si los precios cambian mañana, esta versión conserva los de hoy
    total_congelado = Column(Numeric(14, 2), nullable=False)
    datos_inmutables = Column(JSON, nullable=False) # Copia de cliente, grupos y precios
    
    cotizacion = relationship("CotizacionBorrador")
