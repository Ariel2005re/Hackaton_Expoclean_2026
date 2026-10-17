from app.db.database import engine, Base
from app.models import config

print("Creando tablas en la base de datos...")
Base.metadata.create_all(bind=engine)
print("¡Migración inicial completada!")