# app/main_dev.py
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()   # carga .env al inicio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exception_handlers import http_exception_handler

from app.database import Base, engine
from app.auth.routes import router as auth_router
from app.ads.routes import router as ads_router
from app.admin.routes import router as admin_router

# Crear tablas si no existen (solo desarrollo)
Base.metadata.create_all(bind=engine)

# ESTA es la variable que uvicorn busca 👇
app = FastAPI(title="DeOtraMano API (Dev)")

# === CORS ===
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Static ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]   # .../deotramano_fastapi
STATIC_DIR = PROJECT_ROOT / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# === Routers ===
app.include_router(auth_router,  prefix="/api/auth",  tags=["Auth"])
app.include_router(ads_router,   prefix="/api/ads",   tags=["Ads"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

# === Frontend SPA (Vite build en frontend/dist) ===
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    p = request.url.path
    if (
        frontend_dist.is_dir()
        and (frontend_dist / "index.html").exists()
        and not p.startswith("/api")
        and not p.startswith("/docs")
        and not p.startswith("/openapi.json")
        and not p.startswith("/static")
    ):
        return FileResponse(frontend_dist / "index.html")
    return await http_exception_handler(request, exc)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main_dev:app", host="0.0.0.0", port=port, reload=True)
