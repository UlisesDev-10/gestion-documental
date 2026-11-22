import uuid
from datetime import datetime, timezone
from typing import Tuple
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.archivo import Archivo
from app.models.usuario import Usuario
from app.models.version import Version
from app.services.lock_service import lock_service
from app.services.storage_service import storage_service


class VersionService:
    @staticmethod
    async def create_new_file_with_v1(
        db: AsyncSession,
        carpeta_id: uuid.UUID,
        nombre: str,
        upload_file: UploadFile,
        comentario: str,
        autor: Usuario
    ) -> Tuple[Archivo, Version]:
        """Crea el registro de archivo y su versión 1 en una sola transacción atómica."""
        sha256_hash, storage_path, tamano_bytes = await storage_service.save_upload_stream(upload_file)

        archivo = Archivo(
            carpeta_id=carpeta_id,
            nombre=nombre,
            en_papelera=False
        )
        db.add(archivo)
        await db.flush()

        v1 = Version(
            archivo_id=archivo.id,
            numero_version=1,
            autor_id=autor.id,
            comentario=comentario,
            tamano_bytes=tamano_bytes,
            sha256_hash=sha256_hash,
            storage_path=storage_path,
            mime_type=upload_file.content_type or "application/octet-stream",
            created_at=datetime.now(timezone.utc)
        )
        db.add(v1)
        await db.flush()

        archivo.version_vigente_id = v1.id
        await db.commit()
        await db.refresh(archivo)
        await db.refresh(v1)
        return archivo, v1

    @staticmethod
    async def add_new_version(
        db: AsyncSession,
        archivo_id: uuid.UUID,
        upload_file: UploadFile,
        comentario: str,
        autor: Usuario
    ) -> Version:
        """Crea una versión consecutiva N+1 y libera automáticamente el bloqueo si lo poseía el autor."""
        # Bloqueo pesimista a nivel de fila
        query = select(Archivo).where(Archivo.id == archivo_id).with_for_update()
        result = await db.execute(query)
        archivo = result.scalar_one_or_none()

        if not archivo or archivo.en_papelera:
            raise NotFoundError("Archivo", "El archivo solicitado no existe o está en la papelera.")

        # Verificar concurrencia
        if lock_service.is_lock_active(archivo) and archivo.bloqueado_por != autor.id:
            raise ConflictError(
                codigo="ARCHIVO_BLOQUEADO",
                mensaje="No puedes subir una versión porque el archivo está bloqueado por otro usuario."
            )

        sha256_hash, storage_path, tamano_bytes = await storage_service.save_upload_stream(upload_file)

        # Determinar número de versión consecutivo
        max_v_query = select(func.max(Version.numero_version)).where(Version.archivo_id == archivo_id)
        max_v = (await db.execute(max_v_query)).scalar_one() or 0
        nuevo_numero = max_v + 1

        nueva_version = Version(
            archivo_id=archivo.id,
            numero_version=nuevo_numero,
            autor_id=autor.id,
            comentario=comentario,
            tamano_bytes=tamano_bytes,
            sha256_hash=sha256_hash,
            storage_path=storage_path,
            mime_type=upload_file.content_type or "application/octet-stream",
            created_at=datetime.now(timezone.utc)
        )
        db.add(nueva_version)
        await db.flush()

        archivo.version_vigente_id = nueva_version.id
        # Si el autor tenía el archivo bloqueado, se libera automáticamente
        if archivo.bloqueado_por == autor.id:
            archivo.bloqueado_por = None
            archivo.bloqueado_en = None
            archivo.bloqueo_expira_en = None

        await db.commit()
        await db.refresh(nueva_version)
        return nueva_version

    @staticmethod
    async def restore_previous_version(
        db: AsyncSession,
        archivo_id: uuid.UUID,
        version_origen_id: uuid.UUID,
        comentario: str,
        autor: Usuario
    ) -> Version:
        """
        Restaura una versión previa creando una versión N+1 idéntica en contenido.
        Preserva intacto todo el historial anterior (Inmutabilidad estricta).
        """
        query = select(Archivo).where(Archivo.id == archivo_id).with_for_update()
        archivo = (await db.execute(query)).scalar_one_or_none()
        if not archivo or archivo.en_papelera:
            raise NotFoundError("Archivo", "El archivo no existe o está en la papelera.")

        v_query = select(Version).where(Version.id == version_origen_id, Version.archivo_id == archivo_id)
        version_origen = (await db.execute(v_query)).scalar_one_or_none()
        if not version_origen:
            raise NotFoundError("Version", "La versión que intentas restaurar no existe.")

        max_v_query = select(func.max(Version.numero_version)).where(Version.archivo_id == archivo_id)
        max_v = (await db.execute(max_v_query)).scalar_one() or 0
        nuevo_numero = max_v + 1

        version_restaurada = Version(
            archivo_id=archivo.id,
            numero_version=nuevo_numero,
            autor_id=autor.id,
            comentario=comentario or f"Restauración a partir de la versión {version_origen.numero_version}",
            tamano_bytes=version_origen.tamano_bytes,
            sha256_hash=version_origen.sha256_hash,
            storage_path=version_origen.storage_path,
            mime_type=version_origen.mime_type,
            created_at=datetime.now(timezone.utc)
        )
        db.add(version_restaurada)
        await db.flush()

        archivo.version_vigente_id = version_restaurada.id
        await db.commit()
        await db.refresh(version_restaurada)
        return version_restaurada


version_service = VersionService()
