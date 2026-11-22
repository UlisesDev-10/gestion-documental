import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.models.archivo import Archivo
from app.models.carpeta import Carpeta
from app.models.usuario import RolUsuario, Usuario
from app.models.version import Version
from app.schemas.archivo import FileMove, FileRead, FileRename
from app.schemas.version import VersionRead, VersionRestoreRequest
from app.services.audit_service import registrar_en_bitacora
from app.services.lock_service import lock_service
from app.services.storage_service import storage_service
from app.services.version_service import version_service

router = APIRouter()

editor_or_admin = require_role([RolUsuario.EDITOR, RolUsuario.ADMINISTRADOR])


def format_file_read(archivo: Archivo, vigente: Optional[Version] = None) -> FileRead:
    version_data = None
    if vigente:
        version_data = VersionRead(
            id=vigente.id,
            archivo_id=vigente.archivo_id,
            numero_version=vigente.numero_version,
            autor_id=vigente.autor_id,
            autor_nombre=vigente.autor.nombre_completo if vigente.autor else None,
            comentario=vigente.comentario,
            tamano_bytes=vigente.tamano_bytes,
            sha256_hash=vigente.sha256_hash,
            mime_type=vigente.mime_type,
            created_at=vigente.created_at,
            es_vigente=True
        )

    is_locked = lock_service.is_lock_active(archivo)
    return FileRead(
        id=archivo.id,
        carpeta_id=archivo.carpeta_id,
        nombre=archivo.nombre,
        version_vigente_id=archivo.version_vigente_id,
        version_vigente=version_data,
        bloqueado=is_locked,
        bloqueado_por_id=archivo.bloqueado_por if is_locked else None,
        bloqueado_por_nombre=archivo.usuario_bloqueo.nombre_completo if (is_locked and archivo.usuario_bloqueo) else None,
        bloqueado_en=archivo.bloqueado_en if is_locked else None,
        bloqueo_expira_en=archivo.bloqueo_expira_en if is_locked else None,
        estado_revision=archivo.estado_revision,
        en_papelera=archivo.en_papelera,
        created_at=archivo.created_at,
        updated_at=archivo.updated_at
    )


@router.get("", response_model=List[FileRead], summary="Listar archivos de una carpeta")
async def list_files_in_folder(
    carpeta_id: uuid.UUID = Query(..., description="ID de la carpeta contenedora"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Archivo)
        .where(Archivo.carpeta_id == carpeta_id, Archivo.en_papelera == False)
        .options(selectinload(Archivo.version_vigente).selectinload(Version.autor), selectinload(Archivo.usuario_bloqueo))
        .order_by(Archivo.nombre.asc())
    )
    result = await db.execute(query)
    archivos = result.scalars().all()
    return [format_file_read(a, a.version_vigente) for a in archivos]


@router.post("/subir", response_model=FileRead, status_code=status.HTTP_201_CREATED, summary="Subida inicial de archivo (v1)")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    carpeta_id: uuid.UUID = Form(...),
    comentario: str = Form(..., min_length=3, max_length=500),
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    # Validar carpeta
    carpeta = (await db.execute(
        select(Carpeta).where(Carpeta.id == carpeta_id, Carpeta.en_papelera == False)
    )).scalar_one_or_none()
    if not carpeta:
        raise NotFoundError("Carpeta", "La carpeta destino no existe.")

    archivo, v1 = await version_service.create_new_file_with_v1(
        db=db,
        carpeta_id=carpeta_id,
        nombre=file.filename or "archivo_sin_nombre",
        upload_file=file,
        comentario=comentario,
        autor=current_user
    )

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="SUBIR_ARCHIVO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={
            "nombre": archivo.nombre,
            "version": 1,
            "sha256": v1.sha256_hash,
            "tamano_bytes": v1.tamano_bytes,
            "comentario": v1.comentario
        },
        request=request
    )

    return format_file_read(archivo, v1)


@router.post("/{archivo_id}/versiones", response_model=VersionRead, status_code=status.HTTP_201_CREATED, summary="Subir nueva versión (N+1)")
async def upload_new_version(
    archivo_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    comentario: str = Form(..., min_length=3, max_length=500),
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    version = await version_service.add_new_version(
        db=db,
        archivo_id=archivo_id,
        upload_file=file,
        comentario=comentario,
        autor=current_user
    )

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="SUBIR_VERSION",
        entidad="version",
        entidad_id=str(version.id),
        detalle={
            "archivo_id": str(archivo_id),
            "version_numero": version.numero_version,
            "sha256": version.sha256_hash,
            "tamano_bytes": version.tamano_bytes,
            "comentario": version.comentario
        },
        request=request
    )

    return VersionRead(
        id=version.id,
        archivo_id=version.archivo_id,
        numero_version=version.numero_version,
        autor_id=version.autor_id,
        autor_nombre=current_user.nombre_completo,
        comentario=version.comentario,
        tamano_bytes=version.tamano_bytes,
        sha256_hash=version.sha256_hash,
        mime_type=version.mime_type,
        created_at=version.created_at,
        es_vigente=True
    )


@router.get("/{archivo_id}", response_model=FileRead, summary="Consultar metadatos de archivo")
async def get_file_metadata(
    archivo_id: uuid.UUID,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Archivo)
        .where(Archivo.id == archivo_id, Archivo.en_papelera == False)
        .options(selectinload(Archivo.version_vigente).selectinload(Version.autor), selectinload(Archivo.usuario_bloqueo))
    )
    archivo = (await db.execute(query)).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo solicitado no existe.")
    return format_file_read(archivo, archivo.version_vigente)


@router.get("/{archivo_id}/descargar", summary="Descargar versión en streaming")
async def download_file_stream(
    archivo_id: uuid.UUID,
    request: Request,
    version_id: Optional[uuid.UUID] = Query(None, description="ID de versión específica o vigencia si se omite"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Archivo).where(Archivo.id == archivo_id, Archivo.en_papelera == False)
    archivo = (await db.execute(query)).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo solicitado no existe.")

    target_version_id = version_id or archivo.version_vigente_id
    if not target_version_id:
        raise NotFoundError("Version", "El archivo no contiene ninguna versión disponible.")

    v_query = select(Version).where(Version.id == target_version_id, Version.archivo_id == archivo_id)
    version = (await db.execute(v_query)).scalar_one_or_none()
    if not version:
        raise NotFoundError("Version", "La versión solicitada no existe.")

    # Auditar descarga
    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="DESCARGAR_ARCHIVO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={
            "archivo_nombre": archivo.nombre,
            "version_numero": version.numero_version,
            "sha256": version.sha256_hash,
            "tamano_bytes": version.tamano_bytes
        },
        request=request
    )

    stream = storage_service.get_file_stream(version.storage_path)
    headers = {
        "Content-Disposition": f'attachment; filename="{archivo.nombre}"',
        "Content-Length": str(version.tamano_bytes),
        "X-Integrity-SHA256": version.sha256_hash,
    }

    return StreamingResponse(
        content=stream,
        media_type=version.mime_type,
        headers=headers
    )


@router.get("/{archivo_id}/versiones", response_model=List[VersionRead], summary="Historial cronológico de versiones")
async def get_version_history(
    archivo_id: uuid.UUID,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    archivo = (await db.execute(
        select(Archivo).where(Archivo.id == archivo_id, Archivo.en_papelera == False)
    )).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo solicitado no existe.")

    query = (
        select(Version)
        .where(Version.archivo_id == archivo_id)
        .options(selectinload(Version.autor))
        .order_by(Version.numero_version.desc())
    )
    result = await db.execute(query)
    versiones = result.scalars().all()

    return [
        VersionRead(
            id=v.id,
            archivo_id=v.archivo_id,
            numero_version=v.numero_version,
            autor_id=v.autor_id,
            autor_nombre=v.autor.nombre_completo if v.autor else None,
            comentario=v.comentario,
            tamano_bytes=v.tamano_bytes,
            sha256_hash=v.sha256_hash,
            mime_type=v.mime_type,
            created_at=v.created_at,
            es_vigente=(v.id == archivo.version_vigente_id)
        )
        for v in versiones
    ]


@router.post("/{archivo_id}/versiones/{version_id}/restaurar", response_model=VersionRead, status_code=status.HTTP_201_CREATED, summary="Restaurar versión previa creando una versión N+1")
async def restore_version(
    archivo_id: uuid.UUID,
    version_id: uuid.UUID,
    data: VersionRestoreRequest,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    nueva_version = await version_service.restore_previous_version(
        db=db,
        archivo_id=archivo_id,
        version_origen_id=version_id,
        comentario=data.comentario,
        autor=current_user
    )

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="RESTAURAR_VERSION",
        entidad="version",
        entidad_id=str(nueva_version.id),
        detalle={
            "archivo_id": str(archivo_id),
            "version_origen_id": str(version_id),
            "nueva_version_numero": nueva_version.numero_version,
            "comentario": nueva_version.comentario
        },
        request=request
    )

    return VersionRead(
        id=nueva_version.id,
        archivo_id=nueva_version.archivo_id,
        numero_version=nueva_version.numero_version,
        autor_id=nueva_version.autor_id,
        autor_nombre=current_user.nombre_completo,
        comentario=nueva_version.comentario,
        tamano_bytes=nueva_version.tamano_bytes,
        sha256_hash=nueva_version.sha256_hash,
        mime_type=nueva_version.mime_type,
        created_at=nueva_version.created_at,
        es_vigente=True
    )


@router.patch("/{archivo_id}/renombrar", response_model=FileRead, summary="Renombrar archivo")
async def rename_file(
    archivo_id: uuid.UUID,
    data: FileRename,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    archivo = (await db.execute(
        select(Archivo).where(Archivo.id == archivo_id, Archivo.en_papelera == False)
    )).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo no existe.")

    if lock_service.is_lock_active(archivo) and archivo.bloqueado_por != current_user.id:
        raise ConflictError(codigo="ARCHIVO_BLOQUEADO", mensaje="El archivo está bloqueado por otro usuario.")

    nombre_antiguo = archivo.nombre
    archivo.nombre = data.nuevo_nombre
    await db.commit()
    await db.refresh(archivo)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="RENOMBRAR_ARCHIVO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={"nombre_anterior": nombre_antiguo, "nombre_nuevo": archivo.nombre},
        request=request
    )

    return format_file_read(archivo, archivo.version_vigente)


@router.patch("/{archivo_id}/mover", response_model=FileRead, summary="Mover archivo a otra carpeta")
async def move_file(
    archivo_id: uuid.UUID,
    data: FileMove,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    archivo = (await db.execute(
        select(Archivo).where(Archivo.id == archivo_id, Archivo.en_papelera == False)
    )).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo no existe.")

    if lock_service.is_lock_active(archivo) and archivo.bloqueado_por != current_user.id:
        raise ConflictError(codigo="ARCHIVO_BLOQUEADO", mensaje="El archivo está bloqueado por otro usuario.")

    destino = (await db.execute(
        select(Carpeta).where(Carpeta.id == data.nueva_carpeta_id, Carpeta.en_papelera == False)
    )).scalar_one_or_none()
    if not destino:
        raise NotFoundError("Carpeta", "La carpeta destino no existe.")

    carpeta_origen = archivo.carpeta_id
    archivo.carpeta_id = data.nueva_carpeta_id
    await db.commit()
    await db.refresh(archivo)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="MOVER_ARCHIVO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={"carpeta_origen": str(carpeta_origen), "carpeta_destino": str(archivo.carpeta_id)},
        request=request
    )

    return format_file_read(archivo, archivo.version_vigente)


@router.delete("/{archivo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Enviar archivo a papelera")
async def delete_file(
    archivo_id: uuid.UUID,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    archivo = (await db.execute(
        select(Archivo).where(Archivo.id == archivo_id, Archivo.en_papelera == False)
    )).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo no existe.")

    if lock_service.is_lock_active(archivo) and archivo.bloqueado_por != current_user.id:
        raise ConflictError(codigo="ARCHIVO_BLOQUEADO", mensaje="No se puede eliminar un archivo bloqueado por otro usuario.")

    archivo.en_papelera = True
    archivo.eliminado_en = datetime.now(timezone.utc)
    # Limpiar bloqueo al enviar a papelera
    archivo.bloqueado_por = None
    archivo.bloqueado_en = None
    archivo.bloqueo_expira_en = None
    await db.commit()

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="ENVIAR_PAPELERA_ARCHIVO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={"nombre": archivo.nombre},
        request=request
    )
    return None
