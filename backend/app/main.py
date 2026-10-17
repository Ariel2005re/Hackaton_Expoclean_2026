from fastapi import FastAPI
from backend.app.routers import config, clientes, cotizaciones, propuestas, versiones

app = FastAPI(title="API Hackathon Expo Clean 2026")

# Conectar las rutas
app.include_router(config.router)
app.include_router(clientes.router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API y Base de Datos conectadas correctamente"}

app.include_router(cotizaciones.router)
app.include_router(propuestas.router)
app.include_router(versiones.router)

from backend.app.extraction.router import extraction_router
app.include_router(extraction_router)
