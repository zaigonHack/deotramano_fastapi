# app/models.py
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Text
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Flags
    is_admin = Column(Boolean, default=False)       # Administrador
    is_blocked = Column(Boolean, default=False)     # Bloqueado

    # ---- Relaciones ----
    # Anuncios de los que es propietario (usa FK ads.user_id)
    ads = relationship(
        "Ad",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Ad.user_id",
    )

    # Anuncios que este usuario (admin) ha revisado (usa FK ads.reviewed_by_id)
    reviewed_ads = relationship(
        "Ad",
        back_populates="reviewed_by",
        foreign_keys="Ad.reviewed_by_id",
        viewonly=True,  # normalmente no asignamos desde aquí
    )

    # Historial de contraseñas (últimas usadas)
    password_history = relationship(
        "PasswordHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=False)

    # Propietario
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Estado de moderación
    # valores típicos: 'active' | 'pending' | 'review' | 'rejected'
    status = Column(String, default="active", nullable=False)

    # Trazabilidad de moderación
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reject_reason = Column(Text, nullable=True)

    # ---- Relaciones ----
    user = relationship(
        "User",
        back_populates="ads",
        foreign_keys=[user_id],
    )

    reviewed_by = relationship(
        "User",
        back_populates="reviewed_ads",
        foreign_keys=[reviewed_by_id],
    )

    images = relationship(
        "AdImage",
        back_populates="ad",
        cascade="all, delete-orphan",
    )


class AdImage(Base):
    __tablename__ = "ad_images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True, nullable=False)
    ad_id = Column(Integer, ForeignKey("ads.id"), nullable=False)

    ad = relationship("Ad", back_populates="images")


class PasswordHistory(Base):
    """
    Guarda hashes de contraseñas anteriores para cada usuario.
    Nos permite evitar que reutilicen las últimas N (p.ej., 3).
    """
    __tablename__ = "password_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="password_history")


# (Opcional) Tabla de logs de moderación si la mapeas con ORM
# Si de momento la manejas con SQL directo, puedes omitir el modelo.
class AdModerationLog(Base):
    __tablename__ = "ad_moderation_log"

    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False)  # 'approve' | 'block' | 'unblock' | 'reject' | 'delete'...
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
