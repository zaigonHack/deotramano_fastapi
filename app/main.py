# app/main.py
import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

# =========================================================
#  Carga de variables .env
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
ENV_LOCAL_FILE = PROJECT_ROOT / ".env.local"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=False)
if ENV_LOCAL_FILE.exists():
    load_dotenv(ENV_LOCAL_FILE, override=True)

print(
    f"[DeOtraMano] Using env file(s): "
    f"{ENV_FILE if ENV_FILE.exists() else '∅'}, "
    f"{ENV_LOCAL_FILE if ENV_LOCAL_FILE.exists() else '∅'}"
)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exception_handlers import http_exception_handler

from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
try:
    from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
except ImportError:
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware  # type: ignore

from app.database import Base, engine
from app.auth.routes import router as auth_router
from app.ads.routes import router as ads_router
from app.admin.routes import router as admin_router
from app.contact.routes import router as contact_router

# =========================================================
#  Config y seguridad
# =========================================================
ENV = os.getenv("ENV", "dev").lower()
CSP_REPORT_ONLY = os.getenv("CSP_REPORT_ONLY", "true").lower() == "true"
SHOW_ROUTES = os.getenv("SHOW_ROUTES", "false").lower() == "true"
EXPOSE_ROUTES_ENDPOINT = os.getenv("EXPOSE_ROUTES_ENDPOINT", "false").lower() == "true"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        "ALLOWED_HOSTS",
        "*.up.railway.app,localhost,127.0.0.1"
    ).split(",")
    if h.strip()
]

PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "").strip()

def _build_csp() -> str:
    if ENV == "dev":
        connect_src = [
            "'self'",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "ws://localhost:5173",
            "ws://127.0.0.1:5173",
        ]
        script_src = "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
        style_src = "style-src 'self' 'unsafe-inline'"
    else:
        connect_src = ["'self'"]
        if PUBLIC_ORIGIN and PUBLIC_ORIGIN not in ("'self'",):
            connect_src.append(PUBLIC_ORIGIN)
        script_src = "script-src 'self'"
        style_src = "style-src 'self'"

    csp_parts = [
        "default-src 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "img-src 'self' data: blob:",
        "object-src 'none'",
        script_src,
        style_src,
        f"connect-src {' '.join(connect_src)}",
        "font-src 'self' data:",
        "media-src 'self' blob:",
    ]
    return "; ".join(csp_parts)

CSP_VALUE = _build_csp()

# =========================================================
#  App y DB
# =========================================================
# 👇 Importa los modelos ANTES de create_all para que se registren las tablas
from app import models as _models  # noqa: F401

# Crea tablas si no existen (usa la DB que marque DATABASE_URL)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DeOtraMano API",
    docs_url="/docs" if ENV == "dev" else None,
    redoc_url="/redoc" if ENV == "dev" else None,
    openapi_url="/openapi.json" if ENV == "dev" else None,
)

# ---------- CORS ----------
default_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://deotramanofastapi-production.up.railway.app",
    "https://web-production-9a890.up.railway.app",
}
if PUBLIC_ORIGIN:
    default_origins.add(PUBLIC_ORIGIN)

extra = os.getenv("CORS_EXTRA_ORIGINS", "").strip()
if extra:
    default_origins.update(o.strip() for o in extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(default_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- HTTPS + Host de confianza ----------
if ENV == "prod":
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# ---------- Seguridad: headers y CSP ----------
@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=(), interest-cohort=()",
    )
    if ENV == "prod":
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    if ENV == "dev" and CSP_REPORT_ONLY:
        resp.headers["Content-Security-Policy-Report-Only"] = CSP_VALUE
    else:
        resp.headers["Content-Security-Policy"] = CSP_VALUE
    return resp

# ---------- Static ----------
STATIC_DIR = PROJECT_ROOT / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------- Routers (API) ----------
app.include_router(auth_router,    prefix="/api/auth",  tags=["Auth"])
app.include_router(ads_router,     prefix="/api/ads",   tags=["Ads"])
app.include_router(admin_router,   prefix="/api/admin", tags=["Admin"])
app.include_router(contact_router, prefix="/api",       tags=["Contact"])  # /api/contact

# ---------- Healths ----------
@app.get("/health", include_in_schema=False)
def health():
    return JSONResponse({"status": "ok"})

@app.get("/healthz", include_in_schema=False)
def healthz():
    smtp_ok = all([os.getenv("SMTP_HOST"), os.getenv("SMTP_FROM"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASS")])
    storage = "disk"
    if os.getenv("CLOUDINARY_CLOUD_NAME") and os.getenv("CLOUDINARY_API_KEY") and os.getenv("CLOUDINARY_API_SECRET"):
        storage = "cloudinary"
    elif os.getenv("AWS_S3_BUCKET"):
        storage = "s3"
    elif os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        storage = "supabase"
    return {
        "ok": True,
        "env": os.getenv("ENV", "dev"),
        "smtp_configured": smtp_ok,
        "storage": storage
    }

# ---------- SPA (Vite build) ----------
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

def _print_routes_table() -> None:
    print("\n=== RUTAS REGISTRADAS ===")
    rows = []
    for r in app.router.routes:
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", None)
        rows.append((path, ", ".join(sorted(list(methods)))) if methods else (path, ""))
    for path, methods in rows:
        print(f"{methods:>9}  {path}")
    print()

if __name__ == "__main__":
    import uvicorn
    if os.getenv("ENV", "dev").lower() == "prod":
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            reload=False,
            log_level=os.getenv("LOG_LEVEL", "warning"),
            access_log=os.getenv("ACCESS_LOG", "false").lower() == "true",
        )
    else:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            reload=True,
            log_level=os.getenv("LOG_LEVEL", "info"),
            access_log=os.getenv("ACCESS_LOG", "true").lower() == "true",
        )
