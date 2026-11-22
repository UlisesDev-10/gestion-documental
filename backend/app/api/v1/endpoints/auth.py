import uuid
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password
)
from app.models.usuario import Usuario
from app.schemas.auth import (
    LoginRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse
)
from app.schemas.usuario import UserRead
from app.services.audit_service import registrar_en_bitacora

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión con credenciales")
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    query = select(Usuario).where(Usuario.email == credentials.email.lower())
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        await registrar_en_bitacora(
            db=db,
            accion="LOGIN_FALLIDO",
            entidad="sesion",
            detalle={"email": credentials.email, "motivo": "credenciales_invalidas"},
            request=request
        )
        raise AuthenticationError("Correo electrónico o contraseña incorrectos.")

    if not user.activo:
        await registrar_en_bitacora(
            db=db,
            usuario_id=user.id,
            accion="LOGIN_BLOQUEADO",
            entidad="sesion",
            detalle={"motivo": "usuario_desactivado"},
            request=request
        )
        raise AuthenticationError("Tu cuenta se encuentra desactivada. Contacta al administrador.")

    access_token = create_access_token(subject=str(user.id), rol=user.rol.value)
    refresh_token = create_refresh_token(subject=str(user.id))

    await registrar_en_bitacora(
        db=db,
        usuario_id=user.id,
        accion="LOGIN_EXITOSO",
        entidad="sesion",
        detalle={"email": user.email, "rol": user.rol.value},
        request=request
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        usuario=UserRead.model_validate(user)
    )


@router.post("/refresh", response_model=TokenRefreshResponse, summary="Renovar Access Token")
async def refresh_token(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise AuthenticationError("Token de refresco inválido.")
        user_id = uuid.UUID(data.get("sub"))
    except Exception as exc:
        raise AuthenticationError("Token de refresco expirado o inválido.") from exc

    query = select(Usuario).where(Usuario.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.activo:
        raise AuthenticationError("Usuario no disponible para renovación de sesión.")

    new_access_token = create_access_token(subject=str(user.id), rol=user.rol.value)
    return TokenRefreshResponse(
        access_token=new_access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión activa")
async def logout(
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await registrar_en_bitacora(
        db=db,
        usuario_id=current_user.id,
        accion="LOGOUT",
        entidad="sesion",
        detalle={"email": current_user.email},
        request=request
    )
    return None


@router.get("/me", response_model=UserRead, summary="Obtener perfil del usuario autenticado")
async def get_my_profile(current_user: Usuario = Depends(get_current_user)):
    return current_user
