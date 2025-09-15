# app/routers/password_reset.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import secrets

from app.database import get_db
from app.models import User
from app.security import hash_password  # usa tu función para hashear
from app.utils import send_reset_email  # debes tenerla implementada

router = APIRouter(prefix="/api/auth", tags=["auth: password reset"])

RESET_TOKEN_MINUTES = int(os.getenv("RESET_TOKEN_MINUTES", "15"))
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

def _now_utc():
    return datetime.utcnow()

@router.post("/forgot-password")
def forgot_password(payload: dict, request: Request, db: Session = Depends(get_db)):
    """
    payload: { "email": "..." }
    Responde 200 siempre (para no filtrar si el email existe),
    pero si existe, genera token y envía el mail.
    """
    email = (payload or {}).get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email requerido.")

    user = db.query(User).filter(User.email == email).first()

    # Responder 200 aunque no exista (anti enumeración)
    if not user:
        return {"message": "Si el correo existe, te enviamos un email con instrucciones."}

    # Generar token y caducidad
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = _now_utc() + timedelta(minutes=RESET_TOKEN_MINUTES)
    db.commit()

    # Construir enlace para el frontend
    link = f"{FRONTEND_BASE_URL}/reset-password?token={token}"

    # Enviar email real o simulado
    try:
        send_reset_email(user.email, link)
    except Exception:
        # No fallamos el endpoint por un problema de SMTP
        pass

    return {"message": "Si el correo existe, te enviamos un email con instrucciones."}

@router.post("/reset-password")
def reset_password(payload: dict, db: Session = Depends(get_db)):
    """
    payload: {
      "token": "...",
      "new_password": "...",
      "new_password_confirm": "..."
    }
    """
    token = (payload or {}).get("token", "")
    new_password = (payload or {}).get("new_password", "")
    new_password_confirm = (payload or {}).get("new_password_confirm", "")

    if not token:
        raise HTTPException(status_code=400, detail="Falta el token.")
    if not new_password or not new_password_confirm:
        raise HTTPException(status_code=400, detail="Faltan contraseñas.")
    if new_password != new_password_confirm:
        raise HTTPException(status_code=400, detail="Las contraseñas no coinciden.")

    # Política básica (debe coincidir con el front)
    allowed_symbols = "!@#$%^&*()_-+=[]{}:;,.?~"
    import re
    cls = re.escape(allowed_symbols)
    policy = re.compile(rf"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[{cls}])[A-Za-z\d{cls}]{{8,64}}$")
    if not policy.match(new_password):
        raise HTTPException(status_code=400, detail="Contraseña no cumple la política.")

    user = db.query(User).filter(User.reset_token == token).first()
    if not user or not user.reset_token_expires:
        raise HTTPException(status_code=400, detail="Token inválido.")

    if _now_utc() > user.reset_token_expires:
        # invalidar token expirado
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        raise HTTPException(status_code=400, detail="Token caducado. Solicita uno nuevo.")

    # Cambiar contraseña
    user.password_hash = hash_password(new_password)
    # invalidar token
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Contraseña actualizada correctamente."}
