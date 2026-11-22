import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class SearchResultItem(BaseModel):
    tipo: str  # 'archivo' o 'carpeta'
    id: uuid.UUID
    nombre: str
    extension: Optional[str] = None
    carpeta_id: Optional[uuid.UUID] = None
    carpeta_nombre: Optional[str] = None
    version_numero: Optional[int] = None
    autor_nombre: Optional[str] = None
    tamano_bytes: Optional[int] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    total: int
    pagina: int
    limite: int
    elementos: List[SearchResultItem]
