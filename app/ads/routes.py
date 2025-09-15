# app/ads/routes.py
from pathlib import Path
import uuid
import io
import os
import re
from typing import List, Optional, Tuple
from datetime import datetime

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    Query,
    Body,
)
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models
from app.models import User, Ad, AdImage, AdModerationLog
from app.auth.dependencies import get_current_user  # 🔑 autenticación

# Pillow
from PIL import Image, UnidentifiedImageError

# Storage opcional (Cloudinary) si hay credenciales
USE_CLOUDINARY = bool(
    os.getenv("CLOUDINARY_CLOUD_NAME")
    and os.getenv("CLOUDINARY_API_KEY")
    and os.getenv("CLOUDINARY_API_SECRET")
)
if USE_CLOUDINARY:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )

router = APIRouter(tags=["ads"])

# --- DB session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Carpeta ./static/images ===
PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR   = PROJECT_ROOT / "static" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# --- Reglas de imágenes ---
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}

MAX_IMAGES = 9
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

MAX_W = 8000
MAX_H = 8000
TARGET_MAX_SIDE = 2048

# --- Helpers de autorización/estado ---
def ensure_not_blocked(user: User):
    if getattr(user, "is_blocked", False):
        raise HTTPException(
            status_code=403,
            detail="Tu cuenta está bloqueada. Contacta con soporte."
        )

def ensure_owner_or_admin(current: User, owner_id: int):
    if current.id != owner_id and not getattr(current, "is_admin", False):
        raise HTTPException(status_code=403, detail="No autorizado")

def ensure_ad_editable(ad: models.Ad):
    if getattr(ad, "status", "active") not in ("active", "pending"):
        raise HTTPException(
            status_code=403,
            detail="Este anuncio no se puede editar en este momento."
        )

def ensure_admin(current: User):
    if not getattr(current, "is_admin", False):
        raise HTTPException(status_code=403, detail="Sólo administradores.")

# --- Sanitización básica ---
_tag_re = re.compile(r"<[^>]+>")
def sanitize_text(s: str, max_len: int = 5000) -> str:
    s = (s or "").strip()
    s = _tag_re.sub("", s)
    s = re.sub(r"\s+", " ", s)
    return s[:max_len]

# --- Helpers de imagen (Pillow) ---
def _read_limited(upload: UploadFile, limit_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    data = upload.file.read(limit_bytes + 1)
    if not data:
        raise HTTPException(400, "Archivo vacío.")
    if len(data) > limit_bytes:
        raise HTTPException(400, f"Imagen demasiado grande (máximo {limit_bytes // (1024*1024)} MB).")
    return data

def _open_validate_clean(buf: bytes) -> Tuple[Image.Image, str]:
    try:
        bio = io.BytesIO(buf)
        img = Image.open(bio)
    except UnidentifiedImageError:
        raise HTTPException(400, "El archivo no es una imagen válida.")

    fmt = (img.format or "").upper()
    if fmt not in ALLOWED_PIL_FORMATS:
        raise HTTPException(400, f"Formato no permitido: {fmt or 'desconocido'} (solo JPG/PNG/WebP).")

    w, h = img.size
    if w > MAX_W or h > MAX_H:
        raise HTTPException(400, f"Dimensiones de entrada demasiado grandes ({w}x{h}).")

    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif fmt in ("PNG", "WEBP") and img.mode == "P":
        img = img.convert("RGBA")

    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))

    W, H = clean.size
    max_side = max(W, H)
    if max_side > TARGET_MAX_SIDE:
        scale = TARGET_MAX_SIDE / float(max_side)
        new_w = max(1, int(W * scale))
        new_h = max(1, int(H * scale))
        clean = clean.resize((new_w, new_h), Image.LANCZOS)

    return clean, fmt

def _choose_ext(fmt: str) -> str:
    fmt = fmt.upper()
    if fmt == "JPEG":
        return ".jpg"
    if fmt == "PNG":
        return ".png"
    if fmt == "WEBP":
        return ".webp"
    return ".png"

def _save_image_disk(img: Image.Image, fmt: str) -> str:
    ext = _choose_ext(fmt)
    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = IMAGES_DIR / fname

    fmt = fmt.upper()
    if fmt == "JPEG":
        img.save(fpath, format="JPEG", quality=85, optimize=True, progressive=True)
    elif fmt == "PNG":
        img.save(fpath, format="PNG", optimize=True)
    elif fmt == "WEBP":
        img.save(fpath, format="WEBP", quality=82, method=6)
    else:
        img.save(fpath, format="PNG", optimize=True)
    return f"/static/images/{fname}"

def _save_image_cloudinary(buf: bytes) -> str:
    res = cloudinary.uploader.upload(io.BytesIO(buf), folder="deotramano/ads")
    return res["secure_url"]

def _delete_storage(url: str):
    if not url:
        return
    if USE_CLOUDINARY and "res.cloudinary.com" in url:
        return
    if url.startswith("/"):
        fpath = PROJECT_ROOT / url.lstrip("/")
        if fpath.is_file():
            try:
                fpath.unlink(missing_ok=True)
            except Exception:
                pass

# ======================
#   CREAR ANUNCIO
# ======================
@router.post("/create", status_code=201)
async def create_ad(
    title: str = Form(...),
    description: str = Form(...),
    user_id: int = Form(...),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_not_blocked(current_user)
    ensure_owner_or_admin(current_user, user_id)

    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_IMAGES} imágenes")

    ad = models.Ad(
        title=sanitize_text(title, 200),
        description=sanitize_text(description, 5000),
        user_id=user_id,
        status="pending",
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)

    img_urls = []
    for up in images:
        if (up.content_type or "").lower() not in ALLOWED_MIME:
            raise HTTPException(400, f"Tipo de archivo no permitido: {up.content_type}")

        buf = _read_limited(up, MAX_IMAGE_BYTES)
        clean, fmt = _open_validate_clean(buf)

        if USE_CLOUDINARY:
            url = _save_image_cloudinary(buf)
        else:
            url = _save_image_disk(clean, fmt)

        db.add(models.AdImage(url=url, ad_id=ad.id))
        img_urls.append(url)

    db.commit()
    return {
        "msg": "Anuncio creado exitosamente (pendiente de revisión)",
        "notice": "Tu anuncio se ha enviado para revisión. Normalmente se publica en unos minutos si todo es correcto.",
        "ad_id": ad.id,
        "image_urls": img_urls,
        "status": ad.status,
        "editable": ad.status in ("active", "pending"),
    }

# ======================
#   ANUNCIOS POR USUARIO
# ======================
@router.get("/user/{user_id}")
def get_ads_by_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_not_blocked(current_user)
    ensure_owner_or_admin(current_user, user_id)

    ads = db.query(models.Ad).filter(models.Ad.user_id == user_id).all()
    result = []
    for ad in ads:
        images = [{"id": img.id, "url": img.url} for img in ad.images]
        s = (ad.status or "active").lower()
        result.append({
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "images": images,
            "status": s,
            "editable": s in ("active", "pending"),
            "reject_reason": ad.reject_reason,
            "reviewed_at": ad.reviewed_at.isoformat() if ad.reviewed_at else None,
        })
    return result

# ======================
#   ELIMINAR ANUNCIO
# ======================
@router.delete("/delete/{ad_id}")
def delete_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_not_blocked(current_user)

    ad = db.query(models.Ad).filter(models.Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    ensure_owner_or_admin(current_user, ad.user_id)

    # 0) BORRAR LOGS DE MODERACIÓN que referencian este anuncio (evita FK)
    db.query(AdModerationLog).filter(AdModerationLog.ad_id == ad.id).delete(synchronize_session=False)

    # 1) Elimina imágenes (DB + fichero)
    imgs = db.query(models.AdImage).filter(models.AdImage.ad_id == ad.id).all()
    for img in imgs:
        _delete_storage(img.url)
        db.delete(img)
    db.commit()

    # 2) Elimina el anuncio
    db.delete(ad)
    db.commit()
    return {"msg": "Anuncio eliminado"}

# Compatibilidad con DELETE /api/ads/{id}
@router.delete("/{ad_id}")
def delete_ad_plain(
    ad_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_not_blocked(current_user)

    ad = db.query(models.Ad).filter(models.Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    ensure_owner_or_admin(current_user, ad.user_id)

    # 0) BORRAR LOGS DE MODERACIÓN
    db.query(AdModerationLog).filter(AdModerationLog.ad_id == ad.id).delete(synchronize_session=False)

    # 1) Elimina imágenes (DB + fichero)
    imgs = db.query(models.AdImage).filter(models.AdImage.ad_id == ad.id).all()
    for img in imgs:
        _delete_storage(img.url)
        db.delete(img)
    db.commit()

    # 2) Elimina el anuncio
    db.delete(ad)
    db.commit()
    return {"msg": "Anuncio eliminado"}

# ======================
#   EDITAR ANUNCIO
# ======================
@router.put("/edit/{ad_id}")
async def edit_ad(
    ad_id: int,
    title: str = Form(...),
    description: str = Form(...),
    new_images: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_not_blocked(current_user)

    ad = db.query(models.Ad).filter(models.Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    ensure_owner_or_admin(current_user, ad.user_id)
    ensure_ad_editable(ad)

    ad.title = sanitize_text(title, 200)
    ad.description = sanitize_text(description, 5000)

    if new_images:
        total_existing = db.query(models.AdImage).filter(models.AdImage.ad_id == ad_id).count()
        if total_existing + len(new_images) > MAX_IMAGES:
            raise HTTPException(status_code=400, detail=f"No puedes tener más de {MAX_IMAGES} imágenes")

        for up in new_images:
            if (up.content_type or "").lower() not in ALLOWED_MIME:
                raise HTTPException(400, f"Tipo de archivo no permitido: {up.content_type}")

            buf = _read_limited(up, MAX_IMAGE_BYTES)
            clean, fmt = _open_validate_clean(buf)

            if USE_CLOUDINARY:
                url = _save_image_cloudinary(buf)
            else:
                url = _save_image_disk(clean, fmt)

            db.add(models.AdImage(url=url, ad_id=ad.id))

    db.commit()
    return {
        "msg": "Anuncio actualizado",
        "status": ad.status,
        "editable": ad.status in ("active", "pending"),
    }

# ======================
#   ELIMINAR 1 IMAGEN
# ======================
@router.delete("/delete-image/{image_id}")
def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_not_blocked(current_user)

    img = db.query(models.AdImage).filter(models.AdImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    ad = db.query(models.Ad).filter(models.Ad.id == img.ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    ensure_owner_or_admin(current_user, ad.user_id)
    ensure_ad_editable(ad)

    _delete_storage(img.url)
    db.delete(img)
    db.commit()
    return {"msg": "Imagen eliminada"}

# ======================
#   ELIMINAR TODAS LAS IMÁGENES
# ======================
@router.delete("/delete-all-images/{ad_id}")
def delete_all_images(
    ad_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_not_blocked(current_user)

    ad = db.query(models.Ad).filter(models.Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    ensure_owner_or_admin(current_user, ad.user_id)
    ensure_ad_editable(ad)

    images = db.query(models.AdImage).filter(models.AdImage.ad_id == ad_id).all()
    for img in images:
        _delete_storage(img.url)
        db.delete(img)
    db.commit()
    return {"msg": "Todas las imágenes eliminadas"}

# =================================================
#                  MODERACIÓN (ADMIN)
# =================================================
def _log_moderation(db: Session, ad_id: int, admin_id: int, action: str, reason: Optional[str] = None):
    db.add(AdModerationLog(ad_id=ad_id, admin_id=admin_id, action=action, reason=reason))
    db.commit()

@router.get("/moderation/queue")
def moderation_queue(
    status: str = Query("pending", regex="^(pending|active|rejected|archived)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    ensure_admin(me)
    q = (
        db.query(Ad)
        .filter(Ad.status == status)
        .order_by(Ad.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    result = []
    for a in q:
        result.append({
            "id": a.id,
            "title": a.title,
            "description": a.description[:240] if a.description else "",
            "user_id": a.user_id,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            "reject_reason": a.reject_reason,
            "images": [{"id": im.id, "url": im.url} for im in a.images],
        })
    return {"items": result, "count": len(result), "status": status, "offset": offset, "limit": limit}

@router.post("/moderation/{ad_id}/approve")
def moderation_approve(
    ad_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    ensure_admin(me)
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    ad.status = "active"
    ad.reviewed_by_id = me.id
    ad.reviewed_at = datetime.utcnow()
    ad.reject_reason = None
    db.add(ad)
    db.commit()
    _log_moderation(db, ad_id, me.id, "approved", None)

    return {"message": "Anuncio aprobado", "ad_id": ad.id, "status": ad.status}

@router.post("/moderation/{ad_id}/reject")
def moderation_reject(
    ad_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    ensure_admin(me)
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "Indica un motivo de rechazo.")

    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    ad.status = "rejected"
    ad.reviewed_by_id = me.id
    ad.reviewed_at = datetime.utcnow()
    ad.reject_reason = reason[:500]
    db.add(ad)
    db.commit()
    _log_moderation(db, ad_id, me.id, "rejected", reason[:500])

    return {"message": "Anuncio rechazado", "ad_id": ad.id, "status": ad.status, "reason": ad.reject_reason}

@router.post("/moderation/{ad_id}/archive")
def moderation_archive(
    ad_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    ensure_admin(me)
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    ad.status = "archived"
    ad.reviewed_by_id = me.id
    ad.reviewed_at = datetime.utcnow()
    db.add(ad)
    db.commit()
    _log_moderation(db, ad_id, me.id, "archived", None)

    return {"message": "Anuncio archivado", "ad_id": ad.id, "status": ad.status}

@router.post("/moderation/{ad_id}/restore")
def moderation_restore(
    ad_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    ensure_admin(me)
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    ad.status = "pending"
    ad.reviewed_by_id = me.id
    ad.reviewed_at = datetime.utcnow()
    db.add(ad)
    db.commit()
    _log_moderation(db, ad_id, me.id, "restored", None)

    return {"message": "Anuncio movido a pendiente", "ad_id": ad.id, "status": ad.status}
