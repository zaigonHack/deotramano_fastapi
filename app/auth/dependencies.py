# app/auth/dependencies.py
import os
from pathlib import Path
from typing import Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.database import get_db
from app.models import User

# --- Cargar .env desde la raíz del proyecto (por si main aún no lo cargó) ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../deotramano_fastapi
load_dotenv(PROJECT_ROOT / ".env")

# Debe coincidir con lo usado al emitir el token (/api/auth/login)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está definido en el entorno (.env)")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Para OpenAPI; extrae el Bearer token del header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _find_user_by_sub(db: Session, sub: Union[str, int]) -> Optional[User]:
    """
    sub puede ser id (numérico) o email (tokens antiguos).
    - Preferimos id; si falla el cast y contiene '@', lo tratamos como email.
    """
    # Intento por ID
    try:
        uid = int(str(sub))
        return db.query(User).filter(User.id == uid).first()
    except (ValueError, TypeError):
        pass

    # Por email (compatibilidad con tokens antiguos)
    s = str(sub) if sub is not None else ""
    if "@" in s:
        return db.query(User).filter(User.email == s).first()

    return None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Obtiene el usuario autenticado a partir del token JWT.
    Acepta tokens con `sub=id` (nuevo) o `sub=email` (antiguo).
    Si el usuario está bloqueado, devuelve 403.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exc
    except JWTError:
        # Incluye expiración, firma inválida, etc.
        raise credentials_exc

    user = _find_user_by_sub(db, sub)
    if user is None:
        raise credentials_exc

    if getattr(user, "is_blocked", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está bloqueada. Contacta con soporte.",
        )

    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Verifica que el usuario autenticado sea administrador.
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores")
    return current_user
