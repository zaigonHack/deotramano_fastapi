# app/database.py
import os
from typing import Generator
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Carga .env (local). En Railway las variables vienen del panel.
load_dotenv()

# Lee DATABASE_URL con fallback seguro a SQLite
RAW_DB_URL = (os.getenv("DATABASE_URL", "sqlite:///./deotramano.db") or "").strip()


def _normalize_db_url(url: str) -> str:
    """
    Normaliza la URL de conexión para SQLAlchemy.

    - Railway a veces entrega "postgres://..." → convertir a "postgresql+psycopg://"
      (psycopg3).
    - Si es "postgresql://" sin driver → también a "postgresql+psycopg://".
    - Si es SQLite, devolver tal cual.
    - Para Postgres, añade sslmode=require si no está (desactivar con DB_DISABLE_SSL=true).
    """
    if not url:
        return "sqlite:///./deotramano.db"

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()

    # SQLite → se deja tal cual
    if scheme.startswith("sqlite"):
        return url

    # Solo tratamos Postgres
    if scheme in {"postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
        # Fuerza driver psycopg3
        if scheme == "postgres":
            new_scheme = "postgresql+psycopg"
            rest = url[len("postgres://") :]
            base = f"{new_scheme}://{rest}"
            parsed = urlparse(base)
        elif scheme == "postgresql":
            new_scheme = "postgresql+psycopg"
            rest = url[len("postgresql://") :]
            base = f"{new_scheme}://{rest}"
            parsed = urlparse(base)
        else:
            # ya venía con driver explícito; si es psycopg2 lo cambiamos
            new_scheme = "postgresql+psycopg"

        # sslmode=require salvo que se desactive
        disable_ssl = os.getenv("DB_DISABLE_SSL", "").lower() in {"1", "true", "yes"}
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if not disable_ssl:
            q.setdefault("sslmode", "require")

        rebuilt = parsed._replace(
            scheme=new_scheme,
            query=urlencode(q, doseq=True) if q else "",
        )
        return urlunparse(rebuilt)

    # Otros motores: devolver tal cual
    return url


DATABASE_URL = _normalize_db_url(RAW_DB_URL)

# Crea el engine según el motor
if DATABASE_URL.startswith("sqlite"):
    # SQLite local / de desarrollo
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # necesario para SQLite local
        pool_pre_ping=True,
    )
else:
    # Postgres u otro motor (producción)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # valida conexiones antes de usarlas
        pool_size=5,         # tamaño base del pool
        max_overflow=10,     # conexiones extra temporales
        pool_recycle=1800,   # recicla conexiones cada 30 min
        pool_timeout=30,     # espera hasta 30s antes de levantar error
        # echo="debug",      # si necesitas ver SQL, descomenta
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """Dependency FastAPI para obtener sesión de DB."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
