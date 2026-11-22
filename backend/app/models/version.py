import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, CHAR, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.archivo import Archivo
    from app.models.usuario import Usuario


class Version(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "versiones"

    archivo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("archivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False)
    autor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False
    )
    comentario: Mapped[str] = mapped_column(Text, nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones
    archivo: Mapped["Archivo"] = relationship("Archivo", back_populates="versiones", foreign_keys=[archivo_id])
    autor: Mapped["Usuario"] = relationship("Usuario", back_populates="versiones")
