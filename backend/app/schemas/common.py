from typing import Generic, List, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    pagina: int
    limite: int
    paginas: int
    items: List[T]

    model_config = ConfigDict(from_attributes=True)
