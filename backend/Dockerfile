FROM python:3.12-slim
WORKDIR /workspace
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
CMD ["sh", "-c", "python -m backend.migrate && python -m backend.seed_data && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
