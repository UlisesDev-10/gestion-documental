import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    carpeta_padre_id: Optional[uuid.UUID] = None


class FolderRename(BaseModel):
    nuevo_nombre: str = Field(min_length=1, max_length=255)


class FolderMove(BaseModel):
    nueva_carpeta_padre_id: Optional[uuid.UUID] = None


class FolderRead(BaseModel):
    id: uuid.UUID
    nombre: str
    carpeta_padre_id: Optional[uuid.UUID] = None
    creado_por: uuid.UUID
    en_papelera: bool
    created_at: datetime
    updated_at: datetime
    subcarpetas_count: Optional[int] = 0
    archivos_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
