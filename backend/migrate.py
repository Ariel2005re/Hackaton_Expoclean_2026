"""Create a clean schema and add integration fields to earlier local databases."""

from sqlalchemy import text

from backend.app.db.database import Base, engine
from backend.app.models import config, cotizacion, ia_versiones  # noqa: F401


def migrate():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as db:
        db.execute(text("ALTER TABLE cotizaciones_borrador ADD COLUMN IF NOT EXISTS datos JSON NOT NULL DEFAULT '{}'"))
        db.execute(text("ALTER TABLE propuestas_ia ADD COLUMN IF NOT EXISTS estado_revision JSON"))
        db.execute(text("ALTER TABLE versiones_cotizacion ADD COLUMN IF NOT EXISTS pdf BYTEA"))
        db.execute(text("ALTER TABLE versiones_cotizacion ADD COLUMN IF NOT EXISTS identidad VARCHAR(64)"))
        db.execute(text("ALTER TABLE versiones_cotizacion ALTER COLUMN total_congelado TYPE NUMERIC(14,2) USING round(total_congelado::numeric,2)"))
        db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_version_identidad_idx ON versiones_cotizacion (borrador_id, identidad) WHERE identidad IS NOT NULL"))
        db.execute(text("ALTER TABLE empresa_config ADD COLUMN IF NOT EXISTS margen_porcentaje DOUBLE PRECISION DEFAULT 0"))
        db.execute(text("ALTER TABLE empresa_config ADD COLUMN IF NOT EXISTS impuesto_porcentaje DOUBLE PRECISION DEFAULT 0"))
        db.execute(text("ALTER TABLE tarifas ADD COLUMN IF NOT EXISTS unidad VARCHAR DEFAULT 'USD/hora'"))
        db.execute(text("ALTER TABLE tarifas ADD COLUMN IF NOT EXISTS es_ejemplo BOOLEAN DEFAULT TRUE"))
        db.execute(text("ALTER TABLE perfiles_rendimiento ADD COLUMN IF NOT EXISTS valor_original DOUBLE PRECISION"))
        db.execute(text("ALTER TABLE perfiles_rendimiento ADD COLUMN IF NOT EXISTS unidad_original VARCHAR"))
        db.execute(text("ALTER TABLE perfiles_rendimiento ADD COLUMN IF NOT EXISTS fuente_url VARCHAR"))
        db.execute(text("ALTER TABLE perfiles_rendimiento ADD COLUMN IF NOT EXISTS es_ejemplo BOOLEAN DEFAULT TRUE"))


if __name__ == "__main__":
    migrate()
