from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Excepción base de la plataforma con código de error semántico."""
    def __init__(
        self,
        status_code: int,
        codigo: str,
        mensaje: str,
        detalle: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalle = detalle or {}


class AuthenticationError(AppException):
    def __init__(self, mensaje: str = "Credenciales inválidas o sesión expirada.", detalle: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "AUTENTICACION_FALLIDA", mensaje, detalle)


class PermissionDeniedError(AppException):
    def __init__(self, mensaje: str = "No tienes permisos suficientes para realizar esta acción.", detalle: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_403_FORBIDDEN, "PERMISOS_INSUFICIENTES", mensaje, detalle)


class NotFoundError(AppException):
    def __init__(self, recurso: str = "Recurso", mensaje: Optional[str] = None, detalle: Optional[Dict[str, Any]] = None):
        msg = mensaje or f"{recurso} no encontrado."
        super().__init__(status.HTTP_404_NOT_FOUND, f"{recurso.upper()}_NO_ENCONTRADO", msg, detalle)


class ConflictError(AppException):
    def __init__(self, codigo: str = "CONFLICTO", mensaje: str = "Existe un conflicto con el estado actual del recurso.", detalle: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_409_CONFLICT, codigo, mensaje, detalle)


# Manejadores para FastAPI
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "codigo": exc.codigo,
                "mensaje": exc.mensaje,
                "detalle": exc.detalle
            }
        }
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errores = []
    for err in exc.errors():
        campo = " -> ".join(str(loc) for loc in err.get("loc", []))
        errores.append({"campo": campo, "mensaje": err.get("msg")})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "codigo": "DATOS_INVALIDOS",
                "mensaje": "Los datos enviados no cumplen con el formato requerido.",
                "detalle": {"errores": errores}
            }
        }
    )


async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "codigo": "ERROR_INTERNO",
                "mensaje": "Ocurrió un error inesperado en el servidor. Por favor intenta más tarde.",
                "detalle": {"tipo": type(exc).__name__}
            }
        }
    )
