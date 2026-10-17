from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=True) # P.N o Empresa
    nombre = Column(String, nullable=True)
    ruc = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    correo = Column(String, nullable=True)

class CotizacionBorrador(Base):
    __tablename__ = "cotizaciones_borrador"
    id = Column(String, primary_key=True, index=True) # Usaremos UUID o códigos como "A001"
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    periodo = Column(String, nullable=True) # Mensual, Semanal
    estado = Column(String, default="borrador")
    # Contrato íntegro y editable; permite campos ausentes y valores por corregir.
    datos = Column(JSON, nullable=False, default=dict)
    
    # Relaciones
    cliente = relationship("Cliente")
    grupos = relationship("Grupo", back_populates="cotizacion", cascade="all, delete-orphan")

class Grupo(Base):
    __tablename__ = "grupos"
    id = Column(Integer, primary_key=True, index=True)
    cotizacion_id = Column(String, ForeignKey("cotizaciones_borrador.id"))
    nombre = Column(String, nullable=True) # Ej: Oficinas, Baños
    cantidad = Column(Integer, default=1)
    superficie_fisica = Column(Float, nullable=True)
    dias_semanales = Column(Integer, nullable=True)
    visitas_diarias = Column(Integer, nullable=True)
    estado_confirmacion = Column(String, default="manual") # manual o revisable (IA)

    # Relaciones
    cotizacion = relationship("CotizacionBorrador", back_populates="grupos")
    trabajos = relationship("Trabajo", back_populates="grupo", cascade="all, delete-orphan")
    recursos = relationship("Recurso", back_populates="grupo", cascade="all, delete-orphan")

class Trabajo(Base):
    __tablename__ = "trabajos"
    id = Column(Integer, primary_key=True, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"))
    tipo = Column(String) # "general" o "especializado"
    superficie_usada = Column(Float, nullable=True)
    horas_estimadas = Column(Float, nullable=True)
    personas = Column(Integer, nullable=True)

    grupo = relationship("Grupo", back_populates="trabajos")

class Recurso(Base):
    __tablename__ = "recursos"
    id = Column(Integer, primary_key=True, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"))
    tipo = Column(String) # "propio" o "compartido"
    id_insumo = Column(Integer, nullable=True)
    cantidad = Column(Float, nullable=True)
    costo_unitario = Column(Float, nullable=True)

    grupo = relationship("Grupo", back_populates="recursos")
