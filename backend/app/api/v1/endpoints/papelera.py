import uuid
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import NotFoundError
from app.models.archivo import Archivo
from app.models.carpeta import Carpeta
from app.models.usuario import RolUsuario, Usuario
from app.schemas.archivo import FileRead
from app.schemas.carpeta import FolderRead
from app.schemas.papelera import TrashItem, TrashListResponse
from app.services.audit_service import registrar_en_bitacora

router = APIRouter()

editor_or_admin = require_role([RolUsuario.EDITOR, RolUsuario.ADMINISTRADOR])
admin_only = require_role([RolUsuario.ADMINISTRADOR])


@router.get("", response_model=TrashListResponse, summary="Listar elementos en la papelera")
async def list_trash(
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    # Carpetas en papelera
    c_res = await db.execute(select(Carpeta).where(Carpeta.en_papelera == True).options(selectinload(Carpeta.creador)))
    carpetas = c_res.scalars().all()

    # Archivos en papelera
    a_res = await db.execute(select(Archivo).where(Archivo.en_papelera == True))
    archivos = a_res.scalars().all()

    elementos = []
    for c in carpetas:
        elementos.append(
            TrashItem(
                tipo="carpeta",
                id=c.id,
                nombre=c.nombre,
                carpeta_id=c.carpeta_padre_id,
                eliminado_en=c.eliminado_en,
                creado_por_nombre=c.creador.nombre_completo if c.creador else None
            )
        )

    for a in archivos:
        elementos.append(
            TrashItem(
                tipo="archivo",
                id=a.id,
                nombre=a.nombre,
                carpeta_id=a.carpeta_id,
                eliminado_en=a.eliminado_en
            )
        )

    return TrashListResponse(
        total=len(elementos),
        elementos=elementos
    )


@router.post("/archivos/{archivo_id}/restaurar", response_model=FileRead, summary="Restaurar archivo desde papelera")
async def restore_file_from_trash(
    archivo_id: uuid.UUID,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Archivo)
        .where(Archivo.id == archivo_id, Archivo.en_papelera == True)
        .options(selectinload(Archivo.version_vigente))
    )
    archivo = (await db.execute(query)).scalar_one_or_none()
    if not archivo:
        raise NotFoundError("Archivo", "El archivo no se encuentra en la papelera.")

    # Si la carpeta contenedora fue eliminada, verificar o enviar a raíz
    carpeta = (await db.execute(
        select(Carpeta).where(Carpeta.id == archivo.carpeta_id, Carpeta.en_papelera == False)
    )).scalar_one_or_none()

    if not carpeta:
        # Enviar a carpeta raíz o primera carpeta disponible
        pass

    archivo.en_papelera = False
    archivo.eliminado_en = None
    await db.commit()
    await db.refresh(archivo)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="RESTAURAR_PAPELERA_ARCHIVO",
        entidad="archivo",
        entidad_id=str(archivo.id),
        detalle={"archivo_nombre": archivo.nombre},
        request=request
    )

    return FileRead.model_validate(archivo)


@router.post("/carpetas/{folder_id}/restaurar", response_model=FolderRead, summary="Restaurar carpeta desde papelera")
async def restore_folder_from_trash(
    folder_id: uuid.UUID,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    carpeta = (await db.execute(
        select(Carpeta).where(Carpeta.id == folder_id, Carpeta.en_papelera == True)
    )).scalar_one_or_none()
    if not carpeta:
        raise NotFoundError("Carpeta", "La carpeta no se encuentra en la papelera.")

    carpeta.en_papelera = False
    carpeta.eliminado_en = None
    await db.commit()
    await db.refresh(carpeta)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="RESTAURAR_PAPELERA_CARPETA",
        entidad="carpeta",
        entidad_id=str(carpeta.id),
        detalle={"carpeta_nombre": carpeta.nombre},
        request=request
    )

    return FolderRead.model_validate(carpeta)


@router.delete("/vaciar", status_code=status.HTTP_204_NO_CONTENT, summary="Vaciar papelera (Solo Administrador)")
async def empty_trash(
    request: Request,
    current_admin: Usuario = Depends(admin_only),
    db: AsyncSession = Depends(get_db)
):
    # Eliminar archivos en papelera
    archivos = (await db.execute(select(Archivo).where(Archivo.en_papelera == True))).scalars().all()
    count_archivos = len(archivos)
    for a in archivos:
        await db.delete(a)

    # Eliminar carpetas en papelera
    carpetas = (await db.execute(select(Carpeta).where(Carpeta.en_papelera == True))).scalars().all()
    count_carpetas = len(carpetas)
    for c in carpetas:
        await db.delete(c)

    await db.commit()

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_admin.id,
        accion="VACIAR_PAPELERA",
        entidad="papelera",
        detalle={"archivos_eliminados": count_archivos, "carpetas_eliminadas": count_carpetas},
        request=request
    )
    return None
