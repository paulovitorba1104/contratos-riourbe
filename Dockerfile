# Imagem de produção (Railway): um único serviço serve a API e a SPA —
# ver seção 2 do plano ("monólito modular — um backend, um deploy"). Os
# Dockerfiles em backend/ e frontend/ são só para o docker-compose de
# desenvolvimento local (hot reload em processos separados).

FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /frontend/dist ./app/static

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed_admin && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
