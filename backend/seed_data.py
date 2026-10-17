"""Idempotent examples and source references; never quote SERCOP as a live tariff."""

from backend.app.db.database import SessionLocal
from backend.app.models.config import Factor, PerfilRendimiento, Tarifa, EmpresaConfig

REFERENCES = (
    ("Oficinas", 1.13, "USD por metro cuadrado, sin IVA", "https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2017/01/limpiezatipoI1.pdf"),
    ("Campamentos", 2.05, "USD por m² mensual, sin IVA", "https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2017/04/2.pdf"),
    ("Instituciones educativas", 1.11, "USD por metro cuadrado, sin IVA", "https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2016/03/ficha-tecnica-limpieza-educativas.pdf"),
    ("Áreas externas", 0.64, "USD por metro cuadrado, sin IVA", "https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2023/03/4_LIMPIEZA-AREA-EXTERNA.pdf"),
)


def seed_db():
    with SessionLocal() as db:
        if not db.query(EmpresaConfig).first():
            db.add(EmpresaConfig(nombre="Mi empresa de limpieza", margen_porcentaje=0,
                                 impuesto_porcentaje=0))
        for name, value in (("bueno", 1.0), ("regular", 1.25), ("malo", 1.5)):
            if not db.query(Factor).filter_by(nombre=name).first():
                db.add(Factor(nombre=name, valor=value))
        for name, value, unit, url in REFERENCES:
            if not db.query(PerfilRendimiento).filter_by(nombre=name).first():
                db.add(PerfilRendimiento(
                    nombre=name, m2_por_hora=None, unidad="m²/hora de trabajo",
                    fuente="SERCOP, ficha de referencia", editable=True,
                    valor_original=value, unidad_original=unit, fuente_url=url,
                    es_ejemplo=True,
                ))
        for name in ("Personal general", "Personal especializado"):
            if not db.query(Tarifa).filter_by(descripcion=name).first():
                db.add(Tarifa(descripcion=name, monto=None, unidad="USD/hora de trabajo",
                              es_ejemplo=True))
        db.commit()


if __name__ == "__main__":
    seed_db()
