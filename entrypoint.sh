#!/bin/bash

echo "[🚀] Iniciando servidor FastAPI en el puerto ${PORT:-8000}..."

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level debug

