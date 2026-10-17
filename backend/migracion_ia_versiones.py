from app.db.database import engine, Base
from app.models import ia_versiones
# Importamos cotizacion para que SQLAlchemy sepa de la relación entre tablas
from app.models import cotizacion 

print("Creando tablas de Propuestas IA y Versiones Inmutables...")
Base.metadata.create_all(bind=engine)
print("¡Migración de IA y Versiones completada!")