from sqlalchemy import Column, Integer, String, Float, Boolean
from backend.app.db.database import Base

class EmpresaConfig(Base):
    __tablename__ = "empresa_config"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, default="Mi Empresa de Limpieza")
    ruc = Column(String, nullable=True)
    margen_porcentaje = Column(Float, default=0)
    impuesto_porcentaje = Column(Float, default=0)

class Factor(Base):
    __tablename__ = "factores"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True) # Ej: Riesgo Alto, Turno Nocturno
    valor = Column(Float) # Ej: 1.25, 1.50

class Tarifa(Base):
    __tablename__ = "tarifas"
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String) # Ej: Salario Básico Unificado (SBU)
    monto = Column(Float)
    unidad = Column(String, default="USD/hora")
    es_ejemplo = Column(Boolean, default=True)

class PerfilRendimiento(Base):
    __tablename__ = "perfiles_rendimiento"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    m2_por_hora = Column(Float, nullable=True)
    unidad = Column(String) # Ej: m2/hora
    fuente = Column(String) # Ej: 'SERCOP', 'ISSA', 'Interno'
    editable = Column(Boolean, default=True)
    valor_original = Column(Float, nullable=True)
    unidad_original = Column(String, nullable=True)
    fuente_url = Column(String, nullable=True)
    es_ejemplo = Column(Boolean, default=True)

class PlantillaRecurso(Base):
    __tablename__ = "plantillas_recurso"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    tipo = Column(String) # Ej: propio, compartido
    unidad = Column(String) # Ej: galón, paca, hora
    costo_unitario = Column(Float)
    fuente = Column(String) # Ej: 'Catálogo SERCOP'
