# app/contact/routes.py
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.header import Header
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Form, Request, status
from pydantic import BaseModel, EmailStr

from app.auth.dependencies import get_current_user  # JWT

router = APIRouter(tags=["Contact"])

# --- Config SMTP desde variables de entorno ---
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()            # p.ej. ssl0.ovh.net
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))            # 587 STARTTLS o 465 SSL
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "").strip()            # usuario COMPLETO (email)
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "").strip()
CONTACT_TO = os.getenv("CONTACT_TO", SMTP_FROM or SMTP_USER or "").strip()
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "30"))

# --- Anti-spam básico y rate-limit por IP ---
_last_hit: dict[str, float] = {}

def _is_spammy(text: str) -> bool:
    t = (text or "").lower()
    bad = ["<script", "http://", "https://", "[url", "[link"]
    return any(x in t for x in bad)

class ContactIn(BaseModel):
    subject: str
    message: str
    email: Optional[EmailStr] = None

def _sanitize_header(s: str) -> str:
    return re.sub(r"[\r\n]+", " ", s or "").strip()

def _send_email_utf8(subject: str, body: str, sender: str, to: str) -> None:
    """
    Envío SMTP con verificación de certificado **por NOMBRE** (evita el 502 que veías).
    - STARTTLS en 587 si SMTP_TLS=True
    - SSL directo en 465 si SMTP_TLS=False o puerto 465
    NOTA: NO nos conectamos por IP: usamos siempre el hostname (p.ej. ssl0.ovh.net)
          para que el CN del certificado coincida y no falle la verificación.
    """
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and SMTP_FROM and to):
        raise RuntimeError("smtp_env_missing (revisa SMTP_HOST/USER/PASS/FROM/CONTACT_TO)")

    em = EmailMessage()
    em["Subject"] = str(Header(_sanitize_header(subject), "utf-8"))
    em["From"] = sender or SMTP_FROM
    em["To"] = to
    em.set_content(body or "", subtype="plain", charset="utf-8")

    last_error = None

    def _try_starttls() -> None:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, 587, timeout=SMTP_TIMEOUT) as s:
            s.ehlo()
            # MUY IMPORTANTE: el server_hostname será el self._host (SMTP_HOST),
            # así el cert de OVH (ssl0.ovh.net) valida OK.
            s.starttls(context=ctx)
            s.ehlo()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(em)

    def _try_ssl() -> None:
        ctx = ssl.create_default_context()
        # Aquí también usamos el hostname, no la IP.
        with smtplib.SMTP_SSL(SMTP_HOST, 465, context=ctx, timeout=SMTP_TIMEOUT) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(em)

    try:
        if SMTP_TLS and SMTP_PORT != 465:
            _try_starttls()
        else:
            _try_ssl()
        return
    except Exception as e1:
        last_error = e1
        # Fallback alterno
        try:
            if SMTP_TLS:
                _try_ssl()
            else:
                _try_starttls()
            return
        except Exception as e2:
            last_error = e2

    raise RuntimeError(f"smtp_send_failed: {last_error!r}")

@router.post("/contact", summary="Enviar mensaje de contacto (requiere login)")
async def send_contact(
    request: Request,
    subject: Optional[str] = Form(default=None, alias="subject", max_length=120),
    message: Optional[str] = Form(default=None, alias="message", max_length=2000),
    current_user = Depends(get_current_user),
):
    # Rate-limit (1 req / 15s por IP)
    ip = request.client.host if request.client else "unknown"
    import time
    now = time.time()
    if ip in _last_hit and now - _last_hit[ip] < 15:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Demasiadas peticiones. Espera unos segundos.")
    _last_hit[ip] = now

    # Permite JSON además de Form
    if subject is None or message is None:
        try:
            data = await request.json()
            parsed = ContactIn(**data)
            subject = subject or parsed.subject
            message = message or parsed.message
        except Exception:
            pass

    subject = (subject or "").strip()
    message = (message or "").strip()

    if len(subject) < 3 or len(message) < 10:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Asunto mínimo 3 y mensaje mínimo 10 caracteres.")
    if _is_spammy(subject) or _is_spammy(message):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Contenido no permitido.")

    user_email = getattr(current_user, "email", "") or ""
    user_name  = getattr(current_user, "username", "") or ""
    user_id    = getattr(current_user, "id", "") or ""

    body = (
        "Mensaje desde el formulario de contacto:\n\n"
        f"Usuario: {user_email or user_name or user_id}\n"
        f"Asunto: {subject}\n\n"
        f"{message}\n"
    )

    try:
        _send_email_utf8(
            subject=f"[Contacto] {subject}",
            body=body,
            sender=SMTP_FROM,
            to=CONTACT_TO,
        )
        return {"ok": True, "msg": "Mensaje enviado. ¡Gracias por contactarnos!"}
    except Exception as e:
        # Devolvemos 502 para que el frontend lo muestre como error
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"email_failed: {e}")
