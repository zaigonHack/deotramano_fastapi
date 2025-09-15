# app/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from app.database import SessionLocal
from app.models import PasswordHistory
from app import models
from app.schemas import UserCreate, UserLogin, AdCreate
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
import os
from datetime import datetime, timedelta
import time
import re
import uuid

# *** SIN prefix aquí (el prefix /api/auth lo pone main.py) ***
router = APIRouter(tags=["auth"])

# ---------- Config ----------
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está definido en el entorno (.env)")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS", "6"))

# URL base del frontend para construir el enlace de reset
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
RESET_TOKEN_MINUTES = int(os.getenv("RESET_TOKEN_MINUTES", "15"))  # caducidad del token

# ---------- Rate limiting FORGOT (en memoria) ----------
RL_WINDOW_SECONDS = int(os.getenv("FORGOT_RL_WINDOW_SECONDS", "900"))  # 15 min
RL_MAX_PER_IP = int(os.getenv("FORGOT_RL_MAX_PER_IP", "5"))
RL_MAX_PER_EMAIL = int(os.getenv("FORGOT_RL_MAX_PER_EMAIL", "3"))

_rate_ip: dict[str, list[float]] = {}
_rate_email: dict[str, list[float]] = {}

def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _prune_and_check(bucket: list[float], now: float, window: int, limit: int) -> bool:
    i = 0
    for t in bucket:
        if now - t <= window:
            break
        i += 1
    if i:
        del bucket[:i]
    return len(bucket) >= limit

def _rate_check_forgot(request: Request, email: str) -> None:
    now = time.time()
    ip = _client_ip(request)
    bucket_ip = _rate_ip.setdefault(ip, [])
    if _prune_and_check(bucket_ip, now, RL_WINDOW_SECONDS, RL_MAX_PER_IP):
        raise HTTPException(429, "Demasiadas solicitudes desde esta IP. Inténtalo más tarde.")
    bucket_ip.append(now)

    email_key = (email or "").strip().lower()
    if email_key:
        bucket_em = _rate_email.setdefault(email_key, [])
        if _prune_and_check(bucket_em, now, RL_WINDOW_SECONDS, RL_MAX_PER_EMAIL):
            raise HTTPException(429, "Demasiadas solicitudes para este correo. Inténtalo más tarde.")
        bucket_em.append(now)

# ---------- Rate limiting LOGIN (en memoria) ----------
LOGIN_RL_WINDOW_SECONDS = int(os.getenv("LOGIN_RL_WINDOW_SECONDS", "900"))  # 15 min
LOGIN_RL_MAX_PER_IP = int(os.getenv("LOGIN_RL_MAX_PER_IP", "30"))
LOGIN_RL_MAX_PER_EMAIL = int(os.getenv("LOGIN_RL_MAX_PER_EMAIL", "10"))

_login_rate_ip: dict[str, list[float]] = {}
_login_rate_email: dict[str, list[float]] = {}

def _rate_check_login(request: Request, email: str) -> None:
    now = time.time()
    ip = _client_ip(request)
    bucket_ip = _login_rate_ip.setdefault(ip, [])
    if _prune_and_check(bucket_ip, now, LOGIN_RL_WINDOW_SECONDS, LOGIN_RL_MAX_PER_IP):
        raise HTTPException(429, "Demasiadas solicitudes de login desde esta IP. Inténtalo más tarde.")
    bucket_ip.append(now)

    email_key = (email or "").strip().lower()
    if email_key:
        bucket_em = _login_rate_email.setdefault(email_key, [])
        if _prune_and_check(bucket_em, now, LOGIN_RL_WINDOW_SECONDS, LOGIN_RL_MAX_PER_EMAIL):
            raise HTTPException(429, "Demasiados intentos de login para este correo. Inténtalo más tarde.")
        bucket_em.append(now)

# ---------- Utilidades de validación de contraseñas ----------
_ALLOWED_SYMBOLS = "!@#$%^&*()_-+=[]{}:;,.?~"

def _validate_new_password(pw: str) -> None:
    if not re.fullmatch(rf"^[A-Za-z0-9{re.escape(_ALLOWED_SYMBOLS)}]{{8,64}}$", pw or ""):
        raise HTTPException(
            400,
            detail=(
                "La contraseña debe tener entre 8 y 64 caracteres, sin espacios, "
                "y sólo puede contener letras, números y estos símbolos: " + _ALLOWED_SYMBOLS
            ),
        )
    if not re.search(r"[a-z]", pw):
        raise HTTPException(400, "La contraseña debe incluir al menos una letra minúscula.")
    if not re.search(r"[A-Z]", pw):
        raise HTTPException(400, "La contraseña debe incluir al menos una letra mayúscula.")
    if not re.search(r"[0-9]", pw):
        raise HTTPException(400, "La contraseña debe incluir al menos un dígito.")
    if not re.search(rf"[{re.escape(_ALLOWED_SYMBOLS)}]", pw):
        raise HTTPException(400, f"La contraseña debe incluir al menos un símbolo de: {_ALLOWED_SYMBOLS}")

# ---------- DB session ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Dependencia: usuario actual desde Bearer token ----------
def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "No autenticado")
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub") or 0)
    except JWTError:
        raise HTTPException(401, "Token inválido")
    if not user_id:
        raise HTTPException(401, "Token inválido")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(401, "Usuario no encontrado")
    return user

# ---------- Schemas ----------
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordBody(BaseModel):
    token: str
    new_password: str
    new_password_confirm: str

class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str
    new_password_confirm: str

# ---------- Auth: login & register ----------
@router.post("/login")
def login_user(
    data: UserLogin,
    request: Request,                   # 👈 necesario para rate-limit
    db: Session = Depends(get_db),
):
    # Rate limit
    _rate_check_login(request, data.email)

    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user or not bcrypt.verify(data.password, user.hashed_password):
        # time.sleep(0.25)  # (opcional) pequeña pausa para mitigar enumeración
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    token_data = {
        "sub": str(user.id),
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "surname": user.surname,
            "email": user.email,
            "is_admin": getattr(user, "is_admin", False),
        },
    }

@router.post("/register")
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    if data.email != data.email_confirm:
        raise HTTPException(400, "Los correos no coinciden")
    if data.password != data.password_confirm:
        raise HTTPException(400, "Las contraseñas no coinciden")

    # (Opcional) aplicar la misma política de contraseñas al registrar
    _validate_new_password(data.password)

    existing_user = db.query(models.User).filter(models.User.email == data.email).first()
    if existing_user:
        raise HTTPException(400, "Este email ya está registrado")

    hashed_pw = bcrypt.hash(data.password)
    new_user = models.User(
        email=data.email,
        name=data.name,
        surname=data.surname,
        hashed_password=hashed_pw,
    )
    db.add(new_user)
    db.commit()
    return {"message": "Usuario registrado correctamente"}

# ---------- Cambiar contraseña (sesión actual) ----------
@router.post("/change-password")
def change_password(
    body: ChangePasswordBody,
    me: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1) comprobar actual
    if not bcrypt.verify(body.current_password, me.hashed_password):
        raise HTTPException(400, "Contraseña actual incorrecta")

    # 2) confirmación + política
    if body.new_password != body.new_password_confirm:
        raise HTTPException(400, "La nueva contraseña y su confirmación no coinciden")
    _validate_new_password(body.new_password)

    # 3) comprobar contra últimas 3
    recent_hashes = (
        db.query(PasswordHistory)
        .filter(PasswordHistory.user_id == me.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(3)
        .all()
    )

    for ph in recent_hashes:
        if bcrypt.verify(body.new_password, ph.hashed_password):
            raise HTTPException(
                400,
                "No puedes reutilizar ninguna de tus últimas 3 contraseñas."
            )

    if bcrypt.verify(body.new_password, me.hashed_password):
        raise HTTPException(
            400,
            "La nueva contraseña no puede ser igual a la actual."
        )

    # 4) guardar la contraseña actual en historial
    db.add(PasswordHistory(user_id=me.id, hashed_password=me.hashed_password))

    # 5) actualizar la nueva
    me.hashed_password = bcrypt.hash(body.new_password)
    db.add(me)
    db.commit()

    return {"message": "Contraseña cambiada correctamente."}

# ---------- Password reset (forgot + reset) ----------
def _make_reset_token(user_id: int) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "typ": "pwd_reset",
        "jti": uuid.uuid4().hex,  # opcional: para blacklist si quisieras
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=RESET_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def _parse_reset_token(token: str) -> int:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if data.get("typ") != "pwd_reset":
            raise HTTPException(400, "Token inválido.")
        user_id = int(data.get("sub"))
        return user_id
    except JWTError:
        raise HTTPException(400, "Token inválido o expirado.")

@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Rate limit
    _rate_check_forgot(request, data.email)

    # Si existe el usuario, generamos token y "enviamos" email (aquí en consola)
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if user:
        token = _make_reset_token(user.id)
        reset_url = f"{FRONTEND_BASE_URL}/reset-password?token={token}"
        # Aquí deberías enviar correo real con SMTP/SendGrid/Mailgun
        print("\n" + "=" * 60)
        print(f"[RESET PASSWORD] To: {user.email}")
        print(f"Enlace (caduca en {RESET_TOKEN_MINUTES} min): {reset_url}")
        print("=" * 60 + "\n")

    # Respuesta genérica (no desvela existencia)
    return {"message": "Si el correo existe, se ha enviado un email con instrucciones para recuperar la contraseña."}

@router.post("/reset-password")
def reset_password(
    body: ResetPasswordBody,
    db: Session = Depends(get_db),
):
    if body.new_password != body.new_password_confirm:
        raise HTTPException(400, "La nueva contraseña y su confirmación no coinciden")

    _validate_new_password(body.new_password)

    user_id = _parse_reset_token(body.token)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    user.hashed_password = bcrypt.hash(body.new_password)
    db.commit()
    # Opcional: invalidar jti aquí si implementas blacklist/Redis.
    return {"message": "Contraseña actualizada correctamente."}

# ---------- Crear anuncio (legacy JSON con URLs) ----------
@router.post("/create_ad")
def create_ad(ad: AdCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == ad.user_id).first()
    if not db_user:
        raise HTTPException(404, "Usuario no encontrado")

    new_ad = models.Ad(title=ad.title, user_id=ad.user_id)
    db.add(new_ad)
    db.commit()
    db.refresh(new_ad)

    for url in ad.image_urls:
        new_image = models.AdImage(url=url, ad_id=new_ad.id)
        db.add(new_image)
    db.commit()

    return {"msg": "Anuncio creado exitosamente", "ad_id": new_ad.id}

# ---------- (Opcional) Endpoints admin legacy ----------
@router.get("/admin/ads")
def get_all_ads(db: Session = Depends(get_db)):
    ads = db.query(models.Ad).all()
    return ads

@router.delete("/admin/delete_ad/{ad_id}")
def delete_ad(ad_id: int, db: Session = Depends(get_db)):
    db_ad = db.query(models.Ad).filter(models.Ad.id == ad_id).first()
    if db_ad:
        db.delete(db_ad)
        db.commit()
        return {"msg": "Anuncio eliminado exitosamente"}
    raise HTTPException(404, "Anuncio no encontrado")

@router.get("/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "surname": u.surname,
            "email": u.email,
            "is_admin": getattr(u, "is_admin", False),
        }
        for u in users
    ]

@router.delete("/admin/delete_user/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(404, "Usuario no encontrado")
    db.delete(db_user)
    db.commit()
    return {"msg": "Usuario eliminado exitosamente"}

@router.get("/admin/images")
def get_all_images(db: Session = Depends(get_db)):
    images = db.query(models.AdImage).all()
    return [{"id": img.id, "url": img.url, "ad_id": img.ad_id} for img in images]

@router.delete("/admin/delete_image/{image_id}")
def delete_image(image_id: int, db: Session = Depends(get_db)):
    db_image = db.query(models.AdImage).filter(models.AdImage.id == image_id).first()
    if not db_image:
        raise HTTPException(404, "Imagen no encontrada")
    db.delete(db_image)
    db.commit()
    return {"msg": "Imagen eliminada exitosamente"}
