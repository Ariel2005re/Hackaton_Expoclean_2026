from app.db.database import engine, Base
from app.models import cotizacion

print("Creando tablas de Clientes, Cotizaciones, Grupos y Trabajos...")
Base.metadata.create_all(bind=engine)
print("¡Migración de cotizaciones completada!")