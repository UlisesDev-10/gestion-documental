import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class VersionRead(BaseModel):
    id: uuid.UUID
    archivo_id: uuid.UUID
    numero_version: int
    autor_id: uuid.UUID
    autor_nombre: Optional[str] = None
    comentario: str
    tamano_bytes: int
    sha256_hash: str
    mime_type: str
    created_at: datetime
    es_vigente: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class VersionRestoreRequest(BaseModel):
    comentario: str = Field(min_length=3, max_length=500)
