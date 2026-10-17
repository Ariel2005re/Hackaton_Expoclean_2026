import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import engine, Base, SessionLocal

# Importar todos los modelos para que create_all conozca todas las tablas,
# incluso si solo se ejecuta este archivo de pruebas de forma aislada.
from app.models import config as _config_models  # noqa: F401
from app.models import cotizacion as _cotizacion_models  # noqa: F401
from app.models import ia_versiones as _ia_versiones_models  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def crear_tablas():
    # A09 corre contra PostgreSQL real (el mismo definido en DATABASE_URL /
    # docker-compose), no contra una base en memoria.
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db_fresca():
    """Sesión nueva e independiente, para leer de la base de datos como lo
    haría otro proceso y así confirmar que los datos quedaron realmente
    persistidos (y no solo presentes en la sesión que los escribió)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()