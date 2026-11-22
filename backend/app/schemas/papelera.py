import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TrashItem(BaseModel):
    tipo: str  # 'archivo' o 'carpeta'
    id: uuid.UUID
    nombre: str
    carpeta_id: Optional[uuid.UUID] = None
    eliminado_en: Optional[datetime] = None
    creado_por_nombre: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TrashListResponse(BaseModel):
    total: int
    elementos: List[TrashItem]
