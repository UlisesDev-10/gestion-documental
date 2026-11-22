import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import ConflictError, NotFoundError
from app.models.archivo import Archivo
from app.models.carpeta import Carpeta
from app.models.usuario import RolUsuario, Usuario
from app.schemas.carpeta import FolderCreate, FolderMove, FolderRead, FolderRename
from app.services.audit_service import registrar_en_bitacora

router = APIRouter()

# Escritura en carpetas: Editor y Administrador
editor_or_admin = require_role([RolUsuario.EDITOR, RolUsuario.ADMINISTRADOR])


@router.get("", response_model=List[FolderRead], summary="Listado de carpetas por jerarquía")
async def list_folders(
    carpeta_padre_id: Optional[uuid.UUID] = Query(None, description="ID de la carpeta padre o null para nivel raíz"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Carpeta).where(Carpeta.en_papelera == False)
    if carpeta_padre_id is None:
        query = query.where(Carpeta.carpeta_padre_id == None)
    else:
        query = query.where(Carpeta.carpeta_padre_id == carpeta_padre_id)

    query = query.order_by(Carpeta.nombre.asc())
    result = await db.execute(query)
    carpetas = result.scalars().all()

    items = []
    for c in carpetas:
        sub_count = (await db.execute(
            select(func.count(Carpeta.id)).where(Carpeta.carpeta_padre_id == c.id, Carpeta.en_papelera == False)
        )).scalar_one()
        file_count = (await db.execute(
            select(func.count(Archivo.id)).where(Archivo.carpeta_id == c.id, Archivo.en_papelera == False)
        )).scalar_one()

        item = FolderRead.model_validate(c)
        item.subcarpetas_count = sub_count
        item.archivos_count = file_count
        items.append(item)

    return items


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED, summary="Crear nueva carpeta")
async def create_folder(
    folder_in: FolderCreate,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    if folder_in.carpeta_padre_id:
        padre = (await db.execute(
            select(Carpeta).where(Carpeta.id == folder_in.carpeta_padre_id, Carpeta.en_papelera == False)
        )).scalar_one_or_none()
        if not padre:
            raise NotFoundError("Carpeta", "La carpeta padre especificada no existe.")

    nueva_carpeta = Carpeta(
        nombre=folder_in.nombre,
        carpeta_padre_id=folder_in.carpeta_padre_id,
        creado_por=current_user.id,
        en_papelera=False
    )
    db.add(nueva_carpeta)
    await db.commit()
    await db.refresh(nueva_carpeta)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="CREAR_CARPETA",
        entidad="carpeta",
        entidad_id=str(nueva_carpeta.id),
        detalle={"nombre": nueva_carpeta.nombre, "carpeta_padre_id": str(nueva_carpeta.carpeta_padre_id)},
        request=request
    )

    return FolderRead.model_validate(nueva_carpeta)


@router.patch("/{folder_id}/renombrar", response_model=FolderRead, summary="Renombrar carpeta")
async def rename_folder(
    folder_id: uuid.UUID,
    data: FolderRename,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    carpeta = (await db.execute(
        select(Carpeta).where(Carpeta.id == folder_id, Carpeta.en_papelera == False)
    )).scalar_one_or_none()
    if not carpeta:
        raise NotFoundError("Carpeta", "La carpeta no existe.")

    nombre_antiguo = carpeta.nombre
    carpeta.nombre = data.nuevo_nombre
    await db.commit()
    await db.refresh(carpeta)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="RENOMBRAR_CARPETA",
        entidad="carpeta",
        entidad_id=str(carpeta.id),
        detalle={"nombre_anterior": nombre_antiguo, "nombre_nuevo": carpeta.nombre},
        request=request
    )

    return FolderRead.model_validate(carpeta)


@router.patch("/{folder_id}/mover", response_model=FolderRead, summary="Mover carpeta a otro nivel jerárquico")
async def move_folder(
    folder_id: uuid.UUID,
    data: FolderMove,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    carpeta = (await db.execute(
        select(Carpeta).where(Carpeta.id == folder_id, Carpeta.en_papelera == False)
    )).scalar_one_or_none()
    if not carpeta:
        raise NotFoundError("Carpeta", "La carpeta a mover no existe.")

    if data.nueva_carpeta_padre_id == carpeta.id:
        raise ConflictError(codigo="MOVIMIENTO_CIRCULAR", mensaje="Una carpeta no puede ser hija de sí misma.")

    if data.nueva_carpeta_padre_id:
        nueva_padre = (await db.execute(
            select(Carpeta).where(Carpeta.id == data.nueva_carpeta_padre_id, Carpeta.en_papelera == False)
        )).scalar_one_or_none()
        if not nueva_padre:
            raise NotFoundError("Carpeta", "La carpeta destino no existe.")

    padre_anterior = carpeta.carpeta_padre_id
    carpeta.carpeta_padre_id = data.nueva_carpeta_padre_id
    await db.commit()
    await db.refresh(carpeta)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="MOVER_CARPETA",
        entidad="carpeta",
        entidad_id=str(carpeta.id),
        detalle={"padre_anterior": str(padre_anterior), "nuevo_padre": str(carpeta.carpeta_padre_id)},
        request=request
    )

    return FolderRead.model_validate(carpeta)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Enviar carpeta a papelera")
async def delete_folder(
    folder_id: uuid.UUID,
    request: Request,
    current_user: Usuario = Depends(editor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    carpeta = (await db.execute(
        select(Carpeta).where(Carpeta.id == folder_id, Carpeta.en_papelera == False)
    )).scalar_one_or_none()
    if not carpeta:
        raise NotFoundError("Carpeta", "La carpeta no existe.")

    now = datetime.now(timezone.utc)
    carpeta.en_papelera = True
    carpeta.eliminado_en = now
    await db.commit()

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="ENVIAR_PAPELERA_CARPETA",
        entidad="carpeta",
        entidad_id=str(carpeta.id),
        detalle={"nombre": carpeta.nombre},
        request=request
    )
    return None
