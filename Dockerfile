FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shelf/ shelf/
COPY scripts/ scripts/
RUN python -m scripts.seed_demo
ENV PYTHONUNBUFFERED=1
CMD exec uvicorn shelf.webapp:app --host 0.0.0.0 --port ${PORT:-8080}
