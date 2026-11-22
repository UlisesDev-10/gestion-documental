import uuid
from typing import List
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.models.usuario import RolUsuario, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    """Extrae y valida el usuario activo a partir del Bearer Token."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise AuthenticationError("El token provisto no es un token de acceso válido.")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Token sin identificador de usuario.")
        user_id = uuid.UUID(user_id_str)
    except Exception as exc:
        raise AuthenticationError("Sesión inválida o expirada.") from exc

    query = select(Usuario).where(Usuario.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("El usuario de la sesión ya no existe.")
    if not user.activo:
        raise AuthenticationError("El usuario se encuentra desactivado.")

    return user


def require_role(roles_permitidos: List[RolUsuario]):
    """Fábrica de dependencias que asegura que el usuario posea uno de los roles permitidos."""
    async def role_checker(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.rol not in roles_permitidos:
            raise PermissionDeniedError(
                mensaje=f"Tu rol actual ({current_user.rol.value}) no tiene autorización para esta operación."
            )
        return current_user
    return role_checker
