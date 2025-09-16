# scripts/create_admin.py
import os
import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

# Asegura imports estilo "from app..." aunque ejecutes como módulo
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, Base, engine
from app import models




def mask_url(url: str) -> str:
    """Enmascara user:pass en una URL para logs amigables."""
    try:
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url)
        netloc = p.hostname or ""
        if p.username or p.password:
            netloc = f"{'***' if p.username else ''}:{'***' if p.password else ''}@{p.hostname}"
        if p.port:
            netloc += f":{p.port}"
        return urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))
    except Exception:
        return url


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def resolve_password_attr() -> str:
    """
    Devuelve el nombre del atributo de password que realmente
    existe en models.User. Soporta: password_hash, hashed_password, password.
    """
    candidates = ("password_hash", "hashed_password", "password")
    for name in candidates:
        if hasattr(models.User, name):
            return name
    # Como último recurso, lanza un error claro
    raise RuntimeError(
        "No encuentro un atributo de password en models.User. "
        "Prueba a renombrar el campo en el script o revisa tu modelo."
    )


def main():
    parser = argparse.ArgumentParser(description="Crear/actualizar usuario admin.")
    parser.add_argument("--email", required=True, help="Email del admin")
    parser.add_argument("--password", required=True, help="Password en texto plano (se hará hash)")
    parser.add_argument("--name", default="Admin", help="Nombre")
    parser.add_argument("--surname", default="User", help="Apellidos")
    parser.add_argument("--force-admin", action="store_true", help="Forzar is_admin=True aunque exista")
    args = parser.parse_args()

    # Info de conexión (enmascarada)
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        print(f"[INFO] Usando DATABASE_URL: {mask_url(db_url)}")

    # Crea tablas por si la DB está vacía
    Base.metadata.create_all(bind=engine)

    password_attr = resolve_password_attr()

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == args.email).first()
        if user:
            # Actualiza password y privilegios si se pide
            setattr(user, password_attr, get_password_hash(args.password))
            if args.force_admin and hasattr(user, "is_admin"):
                user.is_admin = True
            if getattr(user, "name", None) in (None, ""):
                user.name = args.name
            if getattr(user, "surname", None) in (None, ""):
                user.surname = args.surname

            db.add(user)
            db.commit()
            print(f"[OK] Usuario EXISTENTE actualizado: {user.email}  is_admin={getattr(user, 'is_admin', None)}")
        else:
            # Crea nuevo admin
            payload = {
                "email": args.email,
                "name": args.name,
                "surname": args.surname,
            }

            # Campo de password correcto
            payload[password_attr] = get_password_hash(args.password)

            # Campos opcionales si existen en el modelo
            if hasattr(models.User, "is_admin"):
                payload["is_admin"] = True
            if hasattr(models.User, "is_blocked"):
                payload["is_blocked"] = False
            if hasattr(models.User, "created_at"):
                payload["created_at"] = datetime.now(timezone.utc)

            user = models.User(**payload)
            db.add(user)
            db.commit()
            print(f"[OK] Usuario NUEVO creado como admin: {user.email}")
    except IntegrityError as e:
        db.rollback()
        print("[ERROR] Violación de integridad (¿email duplicado?):", str(e.orig))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
