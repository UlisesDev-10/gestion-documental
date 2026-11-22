from fastapi import APIRouter
from app.api.v1.endpoints import auth, usuarios

api_router = APIRouter()

# Rutas de autenticación
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])

# Rutas de usuarios y roles (disponible bajo /usuarios y alias /users)
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios y Roles"])
api_router.include_router(usuarios.router, prefix="/users", tags=["Usuarios y Roles (Alias)"], include_in_schema=False)
