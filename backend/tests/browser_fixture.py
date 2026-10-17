"""I08 only: real API/DB/review/PDF with a deterministic Gemini transport.

Start explicitly with uvicorn backend.tests.browser_fixture:create_app --factory.
Never loaded by the production entry point. Use a separate test database.
"""

from fastapi import FastAPI

from backend.app.extraction.exceptions import GeminiUnavailableError
from backend.app.extraction.service import ExtractionService
from backend.app.routers import clientes, config, cotizaciones, propuestas, versiones

DESCRIPTION = (
    "8 oficinas con superficie total de 280 m², estado bueno y también malo, "
    "limpieza general los lunes, 1 visita por día. "
    "Una bodega sin medidas. 2 espacios sin identificar."
)


class FixtureGemini:
    def call_gemini(self, text):
        if text != DESCRIPTION:
            raise GeminiUnavailableError("Proveedor simulado no disponible; continuar manualmente.")
        return {"spaces": [
            {"name": "oficinas", "quantity": 8, "total_area_m2": 280,
             "conflicting_conditions": ["bueno", "malo"],
             "cleaning_type": "general", "service_days": ["lunes"], "visits_per_day": 1,
             "source_fragment": DESCRIPTION.split(". ")[0]},
            {"name": "bodega", "source_fragment": "Una bodega sin medidas"},
            {"quantity": 2, "source_fragment": "2 espacios sin identificar"},
        ]}


def create_app():
    app = FastAPI(title="MVP: aceptación I08 con proveedor simulado")
    for router in (clientes.router, config.router, cotizaciones.router,
                   propuestas.router, versiones.router):
        app.include_router(router)
    app.dependency_overrides[propuestas.get_service] = lambda: ExtractionService(client=FixtureGemini())
    return app
