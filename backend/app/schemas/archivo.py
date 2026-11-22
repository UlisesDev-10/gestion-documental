import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.archivo import EstadoRevision
from app.schemas.version import VersionRead


class FileRead(BaseModel):
    id: uuid.UUID
    carpeta_id: uuid.UUID
    nombre: str
    version_vigente_id: Optional[uuid.UUID] = None
    version_vigente: Optional[VersionRead] = None
    bloqueado: bool = False
    bloqueado_por_id: Optional[uuid.UUID] = None
    bloqueado_por_nombre: Optional[str] = None
    bloqueado_en: Optional[datetime] = None
    bloqueo_expira_en: Optional[datetime] = None
    estado_revision: EstadoRevision
    en_papelera: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileRename(BaseModel):
    nuevo_nombre: str = Field(min_length=1, max_length=255)


class FileMove(BaseModel):
    nueva_carpeta_id: uuid.UUID
