import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.usuario import Usuario
    from app.models.archivo import Archivo
    from app.models.permiso import Permiso


class Carpeta(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "carpetas"

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    carpeta_padre_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpetas.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    creado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False
    )
    en_papelera: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    eliminado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    creador: Mapped["Usuario"] = relationship("Usuario", back_populates="carpetas_creadas")
    carpeta_padre: Mapped[Optional["Carpeta"]] = relationship("Carpeta", remote_side="Carpeta.id", back_populates="subcarpetas")
    subcarpetas: Mapped[List["Carpeta"]] = relationship("Carpeta", back_populates="carpeta_padre", cascade="all, delete-orphan")
    archivos: Mapped[List["Archivo"]] = relationship("Archivo", back_populates="carpeta", cascade="all, delete-orphan")
    permisos: Mapped[List["Permiso"]] = relationship("Permiso", back_populates="carpeta", cascade="all, delete-orphan")
