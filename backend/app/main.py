from fastapi import FastAPI
from app.routers import config, clientes
from app.routers import config, clientes, cotizaciones

app = FastAPI(title="API Hackathon Expo Clean 2026")

# Conectar las rutas
app.include_router(config.router)
app.include_router(clientes.router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API y Base de Datos conectadas correctamente"}

app.include_router(cotizaciones.router)