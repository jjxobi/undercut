FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY modeling/ modeling/
COPY api/ api/
COPY scripts/ scripts/
RUN pip install --no-cache-dir .

COPY data/processed/ data/processed/

EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
