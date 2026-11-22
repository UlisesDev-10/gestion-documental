from fastapi import APIRouter
from app.api.v1.endpoints import (
    archivos,
    auth,
    bitacora,
    bloqueos,
    busqueda,
    carpetas,
    papelera,
    usuarios,
)

api_router = APIRouter()

# 1. Autenticación
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])

# 2. Usuarios y Roles (Ruta oficial y alias)
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios y Roles"])
api_router.include_router(usuarios.router, prefix="/users", tags=["Usuarios y Roles (Alias)"], include_in_schema=False)

# 3. Carpetas Jerárquicas
api_router.include_router(carpetas.router, prefix="/carpetas", tags=["Carpetas"])
api_router.include_router(carpetas.router, prefix="/folders", tags=["Carpetas (Alias)"], include_in_schema=False)

# 4. Archivos y Versiones
api_router.include_router(archivos.router, prefix="/archivos", tags=["Archivos y Versiones"])
api_router.include_router(archivos.router, prefix="/files", tags=["Archivos y Versiones (Alias)"], include_in_schema=False)

# 5. Concurrencia y Bloqueos
api_router.include_router(bloqueos.router, tags=["Bloqueos y Concurrencia"])

# 6. Búsqueda por Metadatos
api_router.include_router(busqueda.router, prefix="/busqueda", tags=["Búsqueda"])
api_router.include_router(busqueda.router, prefix="/search", tags=["Búsqueda (Alias)"], include_in_schema=False)

# 7. Papelera de Reciclaje
api_router.include_router(papelera.router, prefix="/papelera", tags=["Papelera"])
api_router.include_router(papelera.router, prefix="/trash", tags=["Papelera (Alias)"], include_in_schema=False)

# 8. Bitácora de Auditoría
api_router.include_router(bitacora.router, prefix="/bitacora", tags=["Bitácora de Auditoría"])
api_router.include_router(bitacora.router, prefix="/audit", tags=["Bitácora de Auditoría (Alias)"], include_in_schema=False)
