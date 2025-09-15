# app/main_prod.py
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()   # Carga variables de entorno en producción si existen

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exception_handlers import http_exception_handler

from app.database import Base, engine
from app.auth.routes import router as auth_router
from app.ads.routes import router as ads_router
from app.admin.routes import router as admin_router  # Panel/admin

# ---------- DB: crea tablas (opcional en prod; mantenlo si te viene bien) ----------
Base.metadata.create_all(bind=engine)

# ---------- FastAPI App ----------
app = FastAPI(title="DeOtraMano API (prod)")  # ESTA variable la busca Uvicorn

# ---------- CORS ----------
# Puedes configurar dominios adicionales con FRONTEND_ORIGINS="https://dom1,https://dom2"
_extra = [s.strip() for s in os.getenv("FRONTEND_ORIGINS", "").split(",") if s.strip()]
ALLOWED_ORIGINS = list({
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://deotramanofastapi-production.up.railway.app",
    "https://web-production-9a890.up.railway.app",
    *(_extra or []),
})
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,    # ¡Nada de "*" si usas credenciales!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Static & Frontend ----------
PROJECT_ROOT = Path(__file__).resolve().parents[1]   # .../deotramano_fastapi
STATIC_DIR   = PROJECT_ROOT / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# En la imagen Docker copiamos el build del frontend a frontend/dist
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    # Sirve directamente el SPA en la raíz
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

# ---------- Routers ----------
app.include_router(auth_router,  prefix="/api/auth",  tags=["Auth"])
app.include_router(ads_router,   prefix="/api/ads",   tags=["Ads"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

# ---------- SPA fallback (solo si tienes frontend/dist) ----------
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    """
    Si existe el build del frontend y la ruta NO empieza por /api|/docs|/openapi.json|/static,
    devolvemos index.html para que el router del SPA gestione la ruta.
    """
    p = request.url.path
    if (
        FRONTEND_DIST.is_dir()
        and (FRONTEND_DIST / "index.html").exists()
        and not p.startswith("/api")
        and not p.startswith("/docs")
        and not p.startswith("/openapi.json")
        and not p.startswith("/static")
    ):
        return FileResponse(FRONTEND_DIST / "index.html")
    return await http_exception_handler(request, exc)

# ---------- Entrypoint local (no se usa en Docker, sí si corres python app/main_prod.py) ----------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main_prod:app", host="0.0.0.0", port=port, reload=False)
