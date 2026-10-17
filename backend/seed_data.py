from app.db.database import SessionLocal
from app.models.config import Factor, PerfilRendimiento, Tarifa

def seed_db():
    db = SessionLocal()
    
    # Verificar si ya hay datos para no duplicar
    if db.query(Factor).count() == 0:
        # 1. Factores de dificultad/riesgo
        factores = [
            Factor(nombre="Estándar / Riesgo Bajo", valor=1.00),
            Factor(nombre="Riesgo Medio / Industrial", valor=1.25),
            Factor(nombre="Riesgo Alto / Biológico", valor=1.50)
        ]
        
        # 2. Los 4 Perfiles SERCOP requeridos
        perfiles = [
            PerfilRendimiento(nombre="Limpieza General Oficinas", m2_por_hora=250.0, unidad="m2/hora", fuente="SERCOP", editable=True),
            PerfilRendimiento(nombre="Limpieza Hospitalaria", m2_por_hora=150.0, unidad="m2/hora", fuente="SERCOP", editable=True),
            PerfilRendimiento(nombre="Limpieza Industrial Bodegas", m2_por_hora=300.0, unidad="m2/hora", fuente="SERCOP", editable=True),
            PerfilRendimiento(nombre="Limpieza Exteriores", m2_por_hora=450.0, unidad="m2/hora", fuente="SERCOP", editable=True)
        ]

        # 3. Tarifa base (Salario Básico)
        tarifas = [
            Tarifa(descripcion="SBU 2026 Ecuador", monto=470.00)
        ]

        db.add_all(factores)
        db.add_all(perfiles)
        db.add_all(tarifas)
        db.commit()
        print("¡Datos iniciales (SERCOP, Factores y Tarifas) insertados correctamente!")
    else:
        print("Los datos ya estaban precargados.")
        
    db.close()

if __name__ == "__main__":
    seed_db()