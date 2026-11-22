import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LockRequest(BaseModel):
    duracion_minutos: Optional[int] = Field(default=30, ge=1, le=1440)


class LockResponse(BaseModel):
    archivo_id: uuid.UUID
    bloqueado: bool
    bloqueado_por_id: Optional[uuid.UUID] = None
    bloqueado_por_nombre: Optional[str] = None
    bloqueado_en: Optional[datetime] = None
    bloqueo_expira_en: Optional[datetime] = None
    mensaje: Optional[str] = None
