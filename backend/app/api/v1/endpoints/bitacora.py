import math
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.bitacora import Bitacora
from app.models.usuario import RolUsuario, Usuario
from app.schemas.bitacora import AuditLogRead
from app.schemas.common import PaginatedResponse

router = APIRouter()

admin_only = require_role([RolUsuario.ADMINISTRADOR])


@router.get("", response_model=PaginatedResponse[AuditLogRead], summary="Consultar bitácora de auditoría (Solo Administrador)")
async def list_audit_logs(
    usuario_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID de usuario"),
    accion: Optional[str] = Query(None, description="Filtrar por acción (ej. SUBIR_ARCHIVO, BLOQUEAR_ARCHIVO)"),
    entidad: Optional[str] = Query(None, description="Filtrar por entidad (ej. archivo, carpeta, sesion)"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha de inicio (ISO 8601)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha de término (ISO 8601)"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    current_admin: Usuario = Depends(admin_only),
    db: AsyncSession = Depends(get_db)
):
    query = select(Bitacora).options(selectinload(Bitacora.usuario))
    count_query = select(func.count(Bitacora.id))

    if usuario_id:
        query = query.where(Bitacora.usuario_id == usuario_id)
        count_query = count_query.where(Bitacora.usuario_id == usuario_id)
    if accion:
        query = query.where(Bitacora.accion == accion)
        count_query = count_query.where(Bitacora.accion == accion)
    if entidad:
        query = query.where(Bitacora.entidad == entidad)
        count_query = count_query.where(Bitacora.entidad == entidad)
    if fecha_desde:
        query = query.where(Bitacora.created_at >= fecha_desde)
        count_query = count_query.where(Bitacora.created_at >= fecha_desde)
    if fecha_hasta:
        query = query.where(Bitacora.created_at <= fecha_hasta)
        count_query = count_query.where(Bitacora.created_at <= fecha_hasta)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (pagina - 1) * limite
    query = query.order_by(Bitacora.created_at.desc()).offset(offset).limit(limite)
    result = await db.execute(query)
    registros = result.scalars().all()

    paginas = math.ceil(total / limite) if total > 0 else 1

    items = [
        AuditLogRead(
            id=r.id,
            usuario_id=r.usuario_id,
            usuario_nombre=r.usuario.nombre_completo if r.usuario else None,
            accion=r.accion,
            entidad=r.entidad,
            entidad_id=r.entidad_id,
            detalle=r.detalle,
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            created_at=r.created_at
        )
        for r in registros
    ]

    return PaginatedResponse(
        total=total,
        pagina=pagina,
        limite=limite,
        paginas=paginas,
        items=items
    )
