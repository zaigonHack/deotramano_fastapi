# ---------- 1) Construye el frontend ----------
FROM node:20 AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Si usas VITE_API_URL en build, pásala como ARG:
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---------- 2) Imagen final con backend ----------
FROM python:3.11-slim AS backend
WORKDIR /app

# Dependencias nativas mínimas (Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
  libjpeg62-turbo zlib1g && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODO el backend
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY static/ ./static/  # si tienes estáticos propios

# 👇 IMPORTANTE: copia el build del frontend al sitio que tu app espera
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Entrypoint Gunicorn
ENV ENV=prod
ENV PORT=8000
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:8000", "app.main:app"]
