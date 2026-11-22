import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.carpeta import Carpeta
    from app.models.usuario import Usuario
    from app.models.version import Version


class EstadoRevision(str, enum.Enum):
    SIN_REVISION = "sin_revision"
    PENDIENTE = "pendiente"
    REVISADO = "revisado"
    CON_OBSERVACIONES = "con_observaciones"


estado_revision_enum = ENUM(
    EstadoRevision,
    name="estado_revision_enum",
    create_type=False
)


class Archivo(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "archivos"

    carpeta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpetas.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    version_vigente_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("versiones.id", ondelete="SET NULL", deferrable=True, initially="DEFERRED"),
        nullable=True
    )
    bloqueado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True
    )
    bloqueado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    bloqueo_expira_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estado_revision: Mapped[EstadoRevision] = mapped_column(
        estado_revision_enum,
        nullable=False,
        default=EstadoRevision.SIN_REVISION
    )
    en_papelera: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    eliminado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    carpeta: Mapped["Carpeta"] = relationship("Carpeta", back_populates="archivos")
    usuario_bloqueo: Mapped[Optional["Usuario"]] = relationship("Usuario", back_populates="archivos_bloqueados")
    versiones: Mapped[List["Version"]] = relationship("Version", back_populates="archivo", foreign_keys="Version.archivo_id", cascade="all, delete-orphan")
    version_vigente: Mapped[Optional["Version"]] = relationship("Version", foreign_keys=[version_vigente_id], post_update=True)
