import uuid
from typing import Any, Dict, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bitacora import Bitacora


async def registrar_en_bitacora(
    db: AsyncSession,
    accion: str,
    entidad: str,
    entidad_id: Optional[str] = None,
    usuario_id: Optional[uuid.UUID] = None,
    detalle: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> Bitacora:
    """Registra una acción auditable de forma append-only en la bitácora."""
    ip_address = None
    user_agent = None

    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    registro = Bitacora(
        usuario_id=usuario_id,
        accion=accion,
        entidad=entidad,
        entidad_id=str(entidad_id) if entidad_id else None,
        detalle=detalle or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(registro)
    await db.commit()
    return registro
