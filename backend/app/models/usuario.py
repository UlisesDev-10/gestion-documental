import enum
from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.carpeta import Carpeta
    from app.models.archivo import Archivo
    from app.models.version import Version
    from app.models.bitacora import Bitacora


class RolUsuario(str, enum.Enum):
    ADMINISTRADOR = "administrador"
    EDITOR = "editor"
    REVISOR = "revisor"
    LECTOR = "lector"


rol_usuario_enum = ENUM(
    RolUsuario,
    name="rol_usuario_enum",
    create_type=False
)


class Usuario(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "usuarios"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(rol_usuario_enum, nullable=False, default=RolUsuario.LECTOR)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relaciones
    carpetas_creadas: Mapped[List["Carpeta"]] = relationship("Carpeta", back_populates="creador")
    versiones: Mapped[List["Version"]] = relationship("Version", back_populates="autor")
    archivos_bloqueados: Mapped[List["Archivo"]] = relationship("Archivo", back_populates="usuario_bloqueo")
    registros_bitacora: Mapped[List["Bitacora"]] = relationship("Bitacora", back_populates="usuario")
