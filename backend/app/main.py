from fastapi import FastAPI

app = FastAPI(title="API Hackathon Expo Clean 2026")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API y Base de Datos conectadas correctamente"}