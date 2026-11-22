import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.usuario import RolUsuario, rol_usuario_enum

if TYPE_CHECKING:
    from app.models.carpeta import Carpeta
    from app.models.usuario import Usuario


class NivelAcceso(str, enum.Enum):
    LECTURA = "lectura"
    EDICION = "edicion"
    ADMINISTRACION = "administracion"


nivel_acceso_enum = ENUM(
    NivelAcceso,
    name="nivel_acceso_enum",
    create_type=False
)


class Permiso(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "permisos"

    carpeta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carpetas.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=True
    )
    rol_tipo: Mapped[Optional[RolUsuario]] = mapped_column(rol_usuario_enum, nullable=True)
    nivel_acceso: Mapped[NivelAcceso] = mapped_column(nivel_acceso_enum, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones
    carpeta: Mapped["Carpeta"] = relationship("Carpeta", back_populates="permisos")
    usuario: Mapped[Optional["Usuario"]] = relationship("Usuario")
