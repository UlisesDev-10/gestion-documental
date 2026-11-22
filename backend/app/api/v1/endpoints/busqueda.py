import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.archivo import Archivo
from app.models.carpeta import Carpeta
from app.models.usuario import Usuario
from app.models.version import Version
from app.schemas.busqueda import SearchResponse, SearchResultItem

router = APIRouter()


@router.get("", response_model=SearchResponse, summary="Búsqueda por metadatos")
async def search_files_and_folders(
    q: Optional[str] = Query(None, description="Término de búsqueda para nombre"),
    extension: Optional[str] = Query(None, description="Filtro por extensión (ej. pdf, docx)"),
    autor_id: Optional[uuid.UUID] = Query(None, description="Filtro por autor de versión o creador"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha de inicio (ISO 8601)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha de término (ISO 8601)"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    offset = (pagina - 1) * limite
    elementos = []

    # 1. Búsqueda de archivos
    arch_query = (
        select(Archivo)
        .where(Archivo.en_papelera == False)
        .options(
            selectinload(Archivo.version_vigente).selectinload(Version.autor),
            selectinload(Archivo.carpeta)
        )
    )

    if q:
        arch_query = arch_query.where(Archivo.nombre.ilike(f"%{q}%"))
    if extension:
        ext = extension.strip().lstrip(".")
        arch_query = arch_query.where(Archivo.nombre.ilike(f"%.{ext}"))
    if fecha_desde:
        arch_query = arch_query.where(Archivo.created_at >= fecha_desde)
    if fecha_hasta:
        arch_query = arch_query.where(Archivo.created_at <= fecha_hasta)
    if autor_id:
        arch_query = arch_query.join(Version, Archivo.version_vigente_id == Version.id).where(Version.autor_id == autor_id)

    arch_query = arch_query.order_by(Archivo.created_at.desc()).offset(offset).limit(limite)
    arch_result = await db.execute(arch_query)
    archivos = arch_result.scalars().all()

    for a in archivos:
        ext = a.nombre.split(".")[-1] if "." in a.nombre else None
        v = a.version_vigente
        elementos.append(
            SearchResultItem(
                tipo="archivo",
                id=a.id,
                nombre=a.nombre,
                extension=ext,
                carpeta_id=a.carpeta_id,
                carpeta_nombre=a.carpeta.nombre if a.carpeta else None,
                version_numero=v.numero_version if v else None,
                autor_nombre=v.autor.nombre_completo if (v and v.autor) else None,
                tamano_bytes=v.tamano_bytes if v else None,
                updated_at=a.updated_at
            )
        )

    # 2. Si no hay filtro de extensión ni autor de versión, buscar también carpetas
    if not extension and not autor_id:
        carp_query = select(Carpeta).where(Carpeta.en_papelera == False)
        if q:
            carp_query = carp_query.where(Carpeta.nombre.ilike(f"%{q}%"))
        if fecha_desde:
            carp_query = carp_query.where(Carpeta.created_at >= fecha_desde)
        if fecha_hasta:
            carp_query = carp_query.where(Carpeta.created_at <= fecha_hasta)

        carp_query = carp_query.order_by(Carpeta.created_at.desc()).limit(limite)
        carp_result = await db.execute(carp_query)
        carpetas = carp_result.scalars().all()

        for c in carpetas:
            elementos.append(
                SearchResultItem(
                    tipo="carpeta",
                    id=c.id,
                    nombre=c.nombre,
                    carpeta_id=c.carpeta_padre_id,
                    updated_at=c.updated_at
                )
            )

    return SearchResponse(
        total=len(elementos),
        pagina=pagina,
        limite=limite,
        elementos=elementos
    )
