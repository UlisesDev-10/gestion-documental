import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.usuario import RolUsuario


class UserBase(BaseModel):
    email: EmailStr
    nombre_completo: str = Field(min_length=2, max_length=255)
    rol: RolUsuario = RolUsuario.LECTOR


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    nombre_completo: Optional[str] = Field(None, min_length=2, max_length=255)
    rol: Optional[RolUsuario] = None
    activo: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class UserRead(UserBase):
    id: uuid.UUID
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
