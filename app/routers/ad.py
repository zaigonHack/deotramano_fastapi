# app/ads/ad.py  (router de anuncios)
import os
import io
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Ad, AdImage, User
from app.auth.dependencies import get_current_user  # 🔐 JWT -> usuario actual

# Validación de imágenes
from PIL import Image, UnidentifiedImageError

router = APIRouter()  # ⬅️ SIN prefix aquí; main.py ya añade /api/ads

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../deotramano_fastapi
UPLOAD_DIR = PROJECT_ROOT / "static" / "images" / "ads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGES = 9


# ---------------------------- DB session ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------- Helpers ----------------------------
def _ensure_user(db: Session, user_id: int) -> User:
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    if bool(getattr(u, "is_blocked", False)):
        raise HTTPException(403, "Tu cuenta está bloqueada.")
    return u


def _ensure_owner_or_admin(current: User, owner_id: int):
    """Permite continuar solo si el usuario es dueño del recurso o admin."""
    if current.id != owner_id and not bool(getattr(current, "is_admin", False)):
        raise HTTPException(status_code=403, detail="No autorizado")


def _validate_image_file(up: UploadFile) -> bytes:
    """
    Lee y valida el archivo de imagen.
    - Límite razonable (Pillow ya corta si es inválida)
    - Comprueba tipo MIME y que realmente sea imagen
    Devuelve los bytes listos para guardar.
    """
    if (up.content_type or "").lower() not in ALLOWED_MIME:
        raise HTTPException(400, f"Tipo de archivo no permitido: {up.content_type}")

    data = up.file.read()  # en rutas síncronas; en async usar await up.read()
    if not data:
        raise HTTPException(400, "Archivo vacío")

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # comprueba integridad
    except UnidentifiedImageError:
        raise HTTPException(400, "El archivo no es una imagen válida")
    except Exception:
        raise HTTPException(400, "Imagen corrupta o no válida")

    # restablece el puntero por si alguien reutiliza el file:
    up.file.seek(0)
    return data


def _filename_for(ad_id: int, idx: int, original: str) -> str:
    ext = (original or "").rsplit(".", 1)[-1].lower() or "jpg"
    return f"ad_{ad_id}_{idx}.{ext}"


# =========================================================
#                       ENDPOINTS
# =========================================================

@router.get("/user/{user_id}")
def list_user_ads(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve los anuncios de un usuario con sus imágenes.
    URL final:  GET /api/ads/user/{user_id}
    """
    _ensure_user(db, user_id)
    _ensure_owner_or_admin(current_user, user_id)

    ads = (
        db.query(Ad)
        .filter(Ad.user_id == user_id)
        .options(joinedload(Ad.images))
        .order_by(Ad.id.desc())
        .all()
    )
    return [
        {
            "id": ad.id,
            "title": ad.title,
            "description": getattr(ad, "description", None) or getattr(ad, "text", None),
            "images": [{"id": im.id, "url": im.url} for im in (ad.images or [])],
        }
        for ad in ads
    ]


@router.post("/create", status_code=201)
async def create_ad(
    title: str = Form(...),
    description: str = Form(...),  # ⚠️ el frontend envía "description"
    user_id: int = Form(...),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crea un anuncio y sube hasta 9 imágenes.
    URL final:  POST /api/ads/create
    """
    user = _ensure_user(db, user_id)
    _ensure_owner_or_admin(current_user, user.id)

    if not title.strip() or not description.strip():
        raise HTTPException(400, "Título y descripción son obligatorios")

    if len(images) == 0:
        raise HTTPException(400, "Sube al menos una imagen")

    if len(images) > MAX_IMAGES:
        raise HTTPException(400, f"Máximo {MAX_IMAGES} imágenes por anuncio")

    # Crea el anuncio (queda pending para revisión si quieres moderación)
    ad = Ad(title=title, description=description, user_id=user.id)
    db.add(ad)
    db.commit()
    db.refresh(ad)

    saved_images: List[AdImage] = []
    for idx, up in enumerate(images, start=1):
        # valida realmente que sea imagen
        data = await up.read()
        if (up.content_type or "").lower() not in ALLOWED_MIME:
            raise HTTPException(400, f"Tipo de archivo no permitido: {up.content_type}")
        try:
            img = Image.open(io.BytesIO(data))
            img.verify()
        except UnidentifiedImageError:
            raise HTTPException(400, "El archivo no es una imagen válida")
        except Exception:
            raise HTTPException(400, "Imagen corrupta o no válida")

        filename = _filename_for(ad.id, idx, up.filename or "")
        fpath = UPLOAD_DIR / filename
        with open(fpath, "wb") as fh:
            fh.write(data)

        rel_url = f"/static/images/ads/{filename}"
        ad_img = AdImage(url=rel_url, ad_id=ad.id)
        db.add(ad_img)
        saved_images.append(ad_img)

    db.commit()

    return {
        "msg": "Anuncio creado",
        "notice": "Tu anuncio ha sido enviado a revisión. Estará visible en unos minutos.",
        "ad_id": ad.id,
        "image_urls": [im.url for im in saved_images],
    }


@router.delete("/delete/{ad_id}", status_code=204)
def delete_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Borra un anuncio del usuario (y sus imágenes físicas).
    URL final:  DELETE /api/ads/delete/{ad_id}
    """
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    _ensure_owner_or_admin(current_user, ad.user_id)

    # borrar ficheros
    images = db.query(AdImage).filter(AdImage.ad_id == ad.id).all()
    for im in images:
        p = PROJECT_ROOT / im.url.lstrip("/")
        try:
            if p.is_file():
                p.unlink(missing_ok=True)
        except Exception:
            pass

    # borrar registros
    db.query(AdImage).filter(AdImage.ad_id == ad.id).delete(synchronize_session=False)
    db.delete(ad)
    db.commit()
    return


@router.delete("/delete-image/{image_id}")
def delete_one_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Borra UNA imagen de un anuncio (usuario).
    URL final:  DELETE /api/ads/delete-image/{image_id}
    """
    im = db.query(AdImage).filter(AdImage.id == image_id).first()
    if not im:
        raise HTTPException(404, "Imagen no encontrada")

    ad = db.query(Ad).filter(Ad.id == im.ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    _ensure_owner_or_admin(current_user, ad.user_id)

    p = PROJECT_ROOT / im.url.lstrip("/")
    try:
        if p.is_file():
            p.unlink(missing_ok=True)
    except Exception:
        pass

    db.delete(im)
    db.commit()
    return {"message": "Imagen eliminada"}


@router.delete("/delete-all-images/{ad_id}")
def delete_all_images(
    ad_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Borra TODAS las imágenes de un anuncio (usuario).
    URL final:  DELETE /api/ads/delete-all-images/{ad_id}
    """
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    _ensure_owner_or_admin(current_user, ad.user_id)

    images = db.query(AdImage).filter(AdImage.ad_id == ad_id).all()
    for im in images:
        p = PROJECT_ROOT / im.url.lstrip("/")
        try:
            if p.is_file():
                p.unlink(missing_ok=True)
        except Exception:
            pass
        db.delete(im)

    db.commit()
    return {"message": "Imágenes eliminadas"}


@router.put("/edit/{ad_id}")
async def edit_ad(
    ad_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    new_images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Edita título/descr. y añade imágenes nuevas.
    URL final:  PUT /api/ads/edit/{ad_id}
    """
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anuncio no encontrado")

    _ensure_owner_or_admin(current_user, ad.user_id)

    if title is not None:
        t = title.strip()
        if not t:
            raise HTTPException(400, "El título no puede estar vacío")
        ad.title = t

    if description is not None:
        d = description.strip()
        if not d:
            raise HTTPException(400, "La descripción no puede estar vacía")
        ad.description = d

    # añadir imágenes nuevas
    if new_images:
        current = db.query(AdImage).filter(AdImage.ad_id == ad.id).count()
        if current + len(new_images) > MAX_IMAGES:
            raise HTTPException(400, f"Máximo {MAX_IMAGES} imágenes por anuncio")

        start = current + 1
        for i, up in enumerate(new_images, start=start):
            # valida realmente que sea imagen
            data = await up.read()
            if (up.content_type or "").lower() not in ALLOWED_MIME:
                raise HTTPException(400, f"Tipo de archivo no permitido: {up.content_type}")
            try:
                img = Image.open(io.BytesIO(data))
                img.verify()
            except UnidentifiedImageError:
                raise HTTPException(400, "El archivo no es una imagen válida")
            except Exception:
                raise HTTPException(400, "Imagen corrupta o no válida")

            filename = _filename_for(ad.id, i, up.filename or "")
            fpath = UPLOAD_DIR / filename
            with open(fpath, "wb") as fh:
                fh.write(data)

            rel_url = f"/static/images/ads/{filename}"
            db.add(AdImage(url=rel_url, ad_id=ad.id))

    db.commit()
    return {"message": "Anuncio actualizado"}
