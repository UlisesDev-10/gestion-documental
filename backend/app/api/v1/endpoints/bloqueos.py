import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import NotFoundError
from app.models.archivo import Archivo
from app.models.usuario import RolUsuario, Usuario
from app.schemas.bloqueo import LockRequest, LockResponse
from app.services.audit_service import registrar_en_bitacora
from app.services.lock_service import lock_service

router = APIRouter()

editor_or_admin = require_role([RolUsuario.EDITOR, RolUsuario.ADMINISTRADOR])
admin_only = require_role([RolUsuario.ADMINISTRADOR])


@router.post("/archivos/{archivo_id}/bloquear", response_model=LockResponse, summary="Bloquear archivo para edición")
async def lock_file(
    archivo_id: uuid.UUID,
    data: LockRequest,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Archivo)
        .where(Archivo.id == archivo_id, Archivo.en_papelera == False)
        .options(selectinload(Archivo.usuario_bloqueo))
        .with_for_update()
    )
    archivo = (await db.execute(query)).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo a bloquear no existe.")

    archivo = await lock_service.acquire_lock(
        db=db,
        archivo=archivo,
        usuario=current_user,
        duracion_minutos=data.duracion_minutos
    )

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="BLOQUEAR_ARCHIVO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={
            "archivo_nombre": archivo.nombre,
            "expira_en": archivo.bloqueo_expira_en.isoformat() if archivo.bloqueo_expira_en else None
        },
        request=request
    )

    return LockResponse(
        archivo_id=archivo.id,
        bloqueado=True,
        bloqueado_por_id=current_user.id,
        bloqueado_por_nombre=current_user.nombre_completo,
        bloqueado_en=archivo.bloqueado_en,
        bloqueo_expira_en=archivo.bloqueo_expira_en,
        mensaje="Archivo bloqueado exitosamente para edición."
    )


@router.post("/archivos/{archivo_id}/desbloquear", response_model=LockResponse, summary="Liberar bloqueo de archivo")
async def unlock_file(
    archivo_id: uuid.UUID,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Archivo)
        .where(Archivo.id == archivo_id, Archivo.en_papelera == False)
        .with_for_update()
    )
    archivo = (await db.execute(query)).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo a desbloquear no existe.")

    archivo = await lock_service.release_lock(db=db, archivo=archivo, usuario=current_user, forzar=False)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="DESBLOQUEAR_ARCHIVO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={"archivo_nombre": archivo.nombre},
        request=request
    )

    return LockResponse(
        archivo_id=archivo.id,
        bloqueado=False,
        mensaje="El bloqueo del archivo ha sido liberado."
    )


@router.post("/archivos/{archivo_id}/forzar-desbloqueo", response_model=LockResponse, summary="Liberación forzada por Administrador")
async def force_unlock_file(
    archivo_id: uuid.UUID,
    request: Request,
    current_admin: Usuario = Depends(admin_only),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Archivo)
        .where(Archivo.id == archivo_id, Archivo.en_papelera == False)
        .with_for_update()
    )
    archivo = (await db.execute(query)).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo no existe.")

    bloqueador_previo = archivo.bloqueado_por
    archivo = await lock_service.release_lock(db=db, archivo=archivo, usuario=current_admin, forzar=True)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_admin.id,
        accion="LIBERACION_FORZADA_BLOQUEO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={"archivo_nombre": archivo.nombre, "bloqueador_previo": str(bloqueador_previo)},
        request=request
    )

    return LockResponse(
        archivo_id=archivo.id,
        bloqueado=False,
        mensaje="Bloqueo liberado forzosamente por el administrador."
    )
