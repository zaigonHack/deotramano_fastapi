# app/admin/routes.py
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from passlib.hash import bcrypt
from sqlalchemy import and_

from app.database import get_db
from app.models import User, Ad, AdImage, AdModerationLog
from app.auth.dependencies import get_current_admin  # ✅ valida Bearer + is_admin

# ⚠️ SIN prefix aquí; el prefix se añade en app/main.py
router = APIRouter(tags=["Admin"])

# Ruta base del proyecto para borrar archivos físicos de imágenes
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../deotramano_fastapi

# ---------- Utilidad email (stub de consola) ----------
def send_email(to: str, subject: str, body: str) -> None:
    # Sustituye por SMTP real si lo deseas
    print(f"[EMAIL] To: {to}\nSubject: {subject}\n\n{body}\n")

# ---------- DTOs ----------
class AdminDeleteUserBody(BaseModel):
    admin_password: str

class BulkIds(BaseModel):
    ids: List[int]

class AdminSetPasswordBody(BaseModel):
    new_password: str
    new_password_confirm: str

class RejectBody(BaseModel):
    reason: str

class CreateAdminBody(BaseModel):
    email: str
    name: Optional[str] = "Admin"
    surname: Optional[str] = "User"
    password: str

class PromoteAdminBody(BaseModel):
    email: str

# ---------- Validación de contraseñas (misma política que auth) ----------
_ALLOWED_SYMBOLS = "!@#$%^&*()_-+=[]{}:;,.?~"

def _validate_new_password(pw: str) -> None:
    import re
    if not re.fullmatch(rf"^[A-Za-z0-9{re.escape(_ALLOWED_SYMBOLS)}]{{8,64}}$", pw or ""):
        raise HTTPException(
            400,
            detail=(
                "La contraseña debe tener entre 8 y 64 caracteres, sin espacios, "
                "y sólo puede contener letras, números y estos símbolos: "
                + _ALLOWED_SYMBOLS
            ),
        )
    if not re.search(r"[a-z]", pw):
        raise HTTPException(400, detail="La contraseña debe incluir al menos una letra minúscula.")
    if not re.search(r"[A-Z]", pw):
        raise HTTPException(400, detail="La contraseña debe incluir al menos una letra mayúscula.")
    if not re.search(r"[0-9]", pw):
        raise HTTPException(400, detail="La contraseña debe incluir al menos un dígito.")
    if not re.search(rf"[{re.escape(_ALLOWED_SYMBOLS)}]", pw):
        raise HTTPException(400, detail=f"La contraseña debe incluir al menos un símbolo de: {_ALLOWED_SYMBOLS}")

# =================================================
#                    USUARIOS
# =================================================

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": getattr(u, "name", None),
            "surname": getattr(u, "surname", None),
            "is_admin": bool(getattr(u, "is_admin", False)),
            "is_blocked": bool(getattr(u, "is_blocked", False)),
        }
        for u in users
    ]

@router.post("/users/{user_id}/block")
def block_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if user_id == admin.id:
        raise HTTPException(400, "No puedes bloquearte a ti mismo.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    user.is_blocked = True
    db.commit()
    return {"message": "Usuario bloqueado"}

@router.post("/users/{user_id}/unblock")
def unblock_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    user.is_blocked = False
    db.commit()
    return {"message": "Usuario desbloqueado"}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    payload: Optional[AdminDeleteUserBody] = Body(default=None),  # body opcional
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if user_id == admin.id:
        raise HTTPException(400, "No puedes eliminarte a ti mismo.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Si se va a borrar un administrador, exige contraseña del admin autenticado
    if bool(getattr(user, "is_admin", False)):
        if not payload or not payload.admin_password:
            raise HTTPException(400, "Se requiere admin_password para borrar un administrador")
        if not bcrypt.verify(payload.admin_password, admin.hashed_password):
            raise HTTPException(401, "Contraseña de administrador incorrecta")

    # 🔧 Evitar 500 por FK: si el usuario tiene anuncios, bórralos con sus imágenes y logs
    ads = (
        db.query(Ad)
        .options(joinedload(Ad.images))
        .filter(Ad.user_id == user.id)
        .all()
    )
    for ad in ads:
        # borrar ficheros físicos
        for img in (ad.images or []):
            fpath = PROJECT_ROOT / img.url.lstrip("/")
            if fpath.is_file():
                try:
                    fpath.unlink(missing_ok=True)
                except Exception:
                    pass
        # borrar registros hijos
        db.query(AdImage).filter(AdImage.ad_id == ad.id).delete(synchronize_session=False)
        db.query(AdModerationLog).filter(AdModerationLog.ad_id == ad.id).delete(synchronize_session=False)
        # borrar el anuncio
        db.delete(ad)

    db.delete(user)
    db.commit()
    return {"message": "Usuario eliminado"}

@router.post("/users/{user_id}/set-password")
def admin_set_user_password(
    user_id: int,
    body: AdminSetPasswordBody,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if body.new_password != body.new_password_confirm:
        raise HTTPException(400, "La nueva contraseña y su confirmación no coinciden")
    _validate_new_password(body.new_password)
    user.hashed_password = bcrypt.hash(body.new_password)
    db.commit()
    return {"message": "Contraseña actualizada para el usuario"}

# ----- Crear un NUEVO admin directamente -----
@router.post("/users/create-admin")
def create_admin_user(
    body: CreateAdminBody,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    email = (body.email or "").strip().lower()
    if not email:
        raise HTTPException(400, "Email requerido")
    _validate_new_password(body.password)

    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(409, "Ya existe un usuario con ese email")

    u = User(
        email=email,
        name=(body.name or "Admin"),
        surname=(body.surname or "User"),
        hashed_password=bcrypt.hash(body.password),
        is_admin=True,
        is_blocked=False,
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"message": "Administrador creado", "user_id": u.id, "email": u.email}

# ----- Elevar a admin un usuario existente por email -----
@router.post("/users/promote-admin")
def promote_admin(
    body: PromoteAdminBody,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    email = (body.email or "").strip().lower()
    u = db.query(User).filter(User.email == email).first()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    u.is_admin = True
    u.is_blocked = False
    db.commit()
    return {"message": "Usuario promovido a admin", "user_id": u.id, "email": u.email}

# =================================================
#                     ANUNCIOS
# =================================================

@router.get("/ads")
def get_all_ads(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ads = (
        db.query(Ad)
        .options(joinedload(Ad.user), joinedload(Ad.images))
        .all()
    )
    return [
        {
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "user_email": ad.user.email if ad.user else None,
            "images": [{"id": im.id, "url": im.url} for im in (ad.images or [])],
            "status": (ad.status or "active"),
            "reject_reason": ad.reject_reason,
            "reviewed_at": ad.reviewed_at.isoformat() if ad.reviewed_at else None,
        }
        for ad in ads
    ]

@router.delete("/ads/{ad_id}")
def delete_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ad = (
        db.query(Ad)
        .options(joinedload(Ad.images))
        .filter(Ad.id == ad_id)
        .first()
    )
    if not ad:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    # 1) Borrar imágenes físicas (best-effort)
    for img in (ad.images or []):
        fpath = PROJECT_ROOT / img.url.lstrip("/")
        if fpath.is_file():
            try:
                fpath.unlink(missing_ok=True)
            except Exception:
                pass

    # 2) Borrar registros hijos para evitar violación de FK en Postgres
    db.query(AdImage).filter(AdImage.ad_id == ad.id).delete(synchronize_session=False)
    db.query(AdModerationLog).filter(AdModerationLog.ad_id == ad.id).delete(synchronize_session=False)

    # 3) Borrar el anuncio
    db.delete(ad)
    db.commit()
    return {"message": "Anuncio eliminado"}

# ✳️ Compatibilidad con AdminPanel actual:
# "block" = mandar a revisión (status -> pending)
@router.post("/ads/{ad_id}/block")
def block_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ad = db.query(Ad).options(joinedload(Ad.user)).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")
    ad.status = "pending"  # mapeo a "pending"
    ad.reviewed_by_id = admin.id
    ad.reviewed_at = datetime.utcnow()
    ad.reject_reason = None
    db.commit()

    db.add(AdModerationLog(ad_id=ad.id, admin_id=admin.id, action="sent_to_pending", reason=None))
    db.commit()

    if ad.user and ad.user.email:
        send_email(
            ad.user.email,
            "Tu anuncio está en revisión",
            f"Hola, tu anuncio '{ad.title}' ha sido movido a revisión por un moderador."
        )
    return {"message": "Anuncio enviado a revisión"}

# "unblock" = activar (status -> active)
@router.post("/ads/{ad_id}/unblock")
def unblock_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")
    ad.status = "active"
    ad.reviewed_by_id = admin.id
    ad.reviewed_at = datetime.utcnow()
    ad.reject_reason = None
    db.commit()

    db.add(AdModerationLog(ad_id=ad.id, admin_id=admin.id, action="approved", reason=None))
    db.commit()

    return {"message": "Anuncio activado"}

# Borrado masivo (con borrado de imágenes, logs y ficheros)
@router.post("/ads/bulk-delete")
def bulk_delete_ads(
    body: BulkIds,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not body.ids:
        return {"deleted": 0}

    items = (
        db.query(Ad)
        .options(joinedload(Ad.images))
        .filter(Ad.id.in_(body.ids))
        .all()
    )
    for ad in items:
        for img in (ad.images or []):
            fpath = PROJECT_ROOT / img.url.lstrip("/")
            if fpath.is_file():
                try:
                    fpath.unlink(missing_ok=True)
                except Exception:
                    pass
        db.query(AdImage).filter(AdImage.ad_id == ad.id).delete(synchronize_session=False)
        db.query(AdModerationLog).filter(AdModerationLog.ad_id == ad.id).delete(synchronize_session=False)
        db.delete(ad)
    db.commit()
    return {"deleted": len(items)}

# --- borrar UNA imagen de un anuncio ---
@router.delete("/ads/{ad_id}/images/{image_id}")
def delete_one_image(
    ad_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    img = db.query(AdImage).filter(
        and_(AdImage.id == image_id, AdImage.ad_id == ad_id)
    ).first()
    if not img:
        raise HTTPException(404, "Imagen no encontrada")

    # borrar archivo físico
    fpath = PROJECT_ROOT / img.url.lstrip("/")
    if fpath.is_file():
        try:
            fpath.unlink(missing_ok=True)
        except Exception:
            pass

    db.delete(img)
    db.commit()
    return {"message": "Imagen eliminada"}

# =================================================
#               MODERACIÓN (ADMIN)
# =================================================

@router.get("/moderation/queue")
def moderation_queue(
    status: str = Query("pending", pattern="^(pending|active|rejected|archived)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    q = (
        db.query(Ad)
        .filter(Ad.status == status)
        .order_by(Ad.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(joinedload(Ad.images), joinedload(Ad.user))
        .all()
    )
    result = []
    for a in q:
        result.append({
            "id": a.id,
            "title": a.title,
            "description": (a.description or "")[:280],
            "user_id": a.user_id,
            "user_email": a.user.email if a.user else None,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            "reject_reason": a.reject_reason,
            "images": [{"id": im.id, "url": im.url} for im in (a.images or [])],
        })
    return {"items": result, "count": len(result), "status": status, "offset": offset, "limit": limit}

@router.post("/moderation/{ad_id}/approve")
def moderation_approve(
    ad_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")
    ad.status = "active"
    ad.reviewed_by_id = admin.id
    ad.reviewed_at = datetime.utcnow()
    ad.reject_reason = None
    db.commit()

    db.add(AdModerationLog(ad_id=ad.id, admin_id=admin.id, action="approved", reason=None))
    db.commit()

    return {"message": "Anuncio aprobado", "ad_id": ad.id, "status": ad.status}

@router.post("/moderation/{ad_id}/reject")
def moderation_reject(
    ad_id: int,
    body: RejectBody,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(400, "Indica un motivo de rechazo.")
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    ad.status = "rejected"
    ad.reviewed_by_id = admin.id
    ad.reviewed_at = datetime.utcnow()
    ad.reject_reason = reason[:500]
    db.commit()

    db.add(AdModerationLog(ad_id=ad.id, admin_id=admin.id, action="rejected", reason=reason[:500]))
    db.commit()

    # (Opcional) avisar al usuario
    if ad.user and ad.user.email:
        send_email(
            ad.user.email,
            "Tu anuncio ha sido rechazado",
            f"Motivo: {ad.reject_reason}\n\nTítulo: {ad.title}"
        )

    return {"message": "Anuncio rechazado", "ad_id": ad.id, "status": ad.status}

@router.post("/moderation/{ad_id}/archive")
def moderation_archive(
    ad_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")
    ad.status = "archived"
    ad.reviewed_by_id = admin.id
    ad.reviewed_at = datetime.utcnow()
    db.commit()

    db.add(AdModerationLog(ad_id=ad.id, admin_id=admin.id, action="archived", reason=None))
    db.commit()

    return {"message": "Anuncio archivado", "ad_id": ad.id, "status": ad.status}

@router.post("/moderation/{ad_id}/restore")
def moderation_restore(
    ad_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")
    ad.status = "pending"
    ad.reviewed_by_id = admin.id
    ad.reviewed_at = datetime.utcnow()
    ad.reject_reason = None
    db.commit()

    db.add(AdModerationLog(ad_id=ad.id, admin_id=admin.id, action="restored", reason=None))
    db.commit()

    return {"message": "Anuncio movido a pendiente", "ad_id": ad.id, "status": ad.status}
