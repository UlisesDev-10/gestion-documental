from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import ConflictError, PermissionDeniedError
from app.models.archivo import Archivo
from app.models.usuario import RolUsuario, Usuario


class LockService:
    @staticmethod
    def is_lock_active(archivo: Archivo) -> bool:
        """Determina si un bloqueo sigue vigente considerando su expiración TTL."""
        if not archivo.bloqueado_por:
            return False
        if not archivo.bloqueo_expira_en:
            return True
        return archivo.bloqueo_expira_en > datetime.now(timezone.utc)

    @classmethod
    async def acquire_lock(
        cls,
        db: AsyncSession,
        archivo: Archivo,
        usuario: Usuario,
        duracion_minutos: Optional[int] = None
    ) -> Archivo:
        """Adquiere el bloqueo exclusivo si el archivo está libre o su bloqueo expiró."""
        now = datetime.now(timezone.utc)
        duracion = duracion_minutos or settings.DEFAULT_LOCK_TTL_MINUTES

        if cls.is_lock_active(archivo) and archivo.bloqueado_por != usuario.id:
            nom_bloqueador = archivo.usuario_bloqueo.nombre_completo if archivo.usuario_bloqueo else "Otro usuario"
            hora = archivo.bloqueado_en.strftime("%H:%M") if archivo.bloqueado_en else "desconocida"
            raise ConflictError(
                codigo="ARCHIVO_BLOQUEADO",
                mensaje=f"El archivo está siendo editado por {nom_bloqueador} desde las {hora}.",
                detalle={
                    "bloqueado_por_id": str(archivo.bloqueado_por),
                    "bloqueado_en": archivo.bloqueado_en.isoformat() if archivo.bloqueado_en else None,
                    "expira_en": archivo.bloqueo_expira_en.isoformat() if archivo.bloqueo_expira_en else None
                }
            )

        archivo.bloqueado_por = usuario.id
        archivo.bloqueado_en = now
        archivo.bloqueo_expira_en = now + timedelta(minutes=duracion)
        await db.commit()
        await db.refresh(archivo)
        return archivo

    @classmethod
    async def release_lock(
        cls,
        db: AsyncSession,
        archivo: Archivo,
        usuario: Usuario,
        forzar: bool = False
    ) -> Archivo:
        """Libera el bloqueo voluntariamente o de forma forzada por el Administrador."""
        if not cls.is_lock_active(archivo):
            archivo.bloqueado_por = None
            archivo.bloqueado_en = None
            archivo.bloqueo_expira_en = None
            await db.commit()
            return archivo

        if forzar:
            if usuario.rol != RolUsuario.ADMINISTRADOR:
                raise PermissionDeniedError("Solo un administrador puede forzar la liberación de bloqueos.")
        else:
            if archivo.bloqueado_por != usuario.id and usuario.rol != RolUsuario.ADMINISTRADOR:
                raise PermissionDeniedError("No puedes liberar un archivo bloqueado por otra persona.")

        archivo.bloqueado_por = None
        archivo.bloqueado_en = None
        archivo.bloqueo_expira_en = None
        await db.commit()
        await db.refresh(archivo)
        return archivo


lock_service = LockService()
