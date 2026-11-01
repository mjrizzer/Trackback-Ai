FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    SERVE_FRONTEND=true ENVIRONMENT=production \
    DATABASE_URL=sqlite:////data/traceback.db UPLOAD_DIR=/data/uploads DEMO_DATA_DIR=/data/demo_data
WORKDIR /app
COPY backend/requirements.lock.txt backend/requirements.lock.txt
RUN pip install --no-cache-dir -r backend/requirements.lock.txt \
    && useradd --create-home --uid 10001 traceback \
    && mkdir -p /data/uploads /data/demo_data && chown -R traceback:traceback /data
COPY backend/ backend/
COPY alembic.ini ./
COPY --from=frontend /build/frontend/dist frontend/dist
USER traceback
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4)"
CMD ["python", "-m", "backend.boot"]
