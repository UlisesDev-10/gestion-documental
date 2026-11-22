import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash
from app.models.usuario import RolUsuario, Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.usuario import UserCreate, UserRead, UserUpdate
from app.services.audit_service import registrar_en_bitacora

router = APIRouter()

# Restricción: exclusivo Administrador
admin_required = require_role([RolUsuario.ADMINISTRADOR])


@router.get("", response_model=PaginatedResponse[UserRead], summary="Listado de usuarios")
async def list_users(
    rol: Optional[RolUsuario] = None,
    activo: Optional[bool] = None,
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    current_admin: Usuario = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    query = select(Usuario)
    count_query = select(func.count(Usuario.id))

    if rol:
        query = query.where(Usuario.rol == rol)
        count_query = count_query.where(Usuario.rol == rol)
    if activo is not None:
        query = query.where(Usuario.activo == activo)
        count_query = count_query.where(Usuario.activo == activo)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (pagina - 1) * limite
    query = query.order_by(Usuario.created_at.desc()).offset(offset).limit(limite)
    result = await db.execute(query)
    users = result.scalars().all()

    paginas = math.ceil(total / limite) if total > 0 else 1

    return PaginatedResponse(
        total=total,
        pagina=pagina,
        limite=limite,
        paginas=paginas,
        items=[UserRead.model_validate(u) for u in users]
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Alta de nuevo usuario")
async def create_user(
    user_in: UserCreate,
    request: Request,
    current_admin: Usuario = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    # Verificar unicidad de correo
    check_query = select(Usuario).where(Usuario.email == user_in.email.lower())
    existing = (await db.execute(check_query)).scalar_one_or_none()
    if existing:
        raise ConflictError(
            codigo="EMAIL_DUPLICADO",
            mensaje=f"Ya existe un usuario registrado con el correo {user_in.email}."
        )

    new_user = Usuario(
        email=user_in.email.lower(),
        password_hash=get_password_hash(user_in.password),
        nombre_completo=user_in.nombre_completo,
        rol=user_in.rol,
        activo=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_admin.id,
        accion="CREAR_USUARIO",
        entidad="usuario",
        entidad_id=str(new_user.id),
        detalle={"email": new_user.email, "rol": new_user.rol.value, "nombre": new_user.nombre_completo},
        request=request
    )

    return new_user


@router.get("/{user_id}", response_model=UserRead, summary="Consultar usuario por ID")
async def get_user(
    user_id: uuid.UUID,
    current_admin: Usuario = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    query = select(Usuario).where(Usuario.id == user_id)
    user = (await db.execute(query)).scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", "El usuario solicitado no existe.")
    return user


@router.patch("/{user_id}", response_model=UserRead, summary="Editar usuario y asignar rol")
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    request: Request,
    current_admin: Usuario = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    query = select(Usuario).where(Usuario.id == user_id)
    user = (await db.execute(query)).scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", "El usuario a actualizar no existe.")

    cambios = {}
    if user_in.nombre_completo is not None:
        user.nombre_completo = user_in.nombre_completo
        cambios["nombre_completo"] = user.nombre_completo
    if user_in.rol is not None:
        user.rol = user_in.rol
        cambios["rol"] = user.rol.value
    if user_in.activo is not None:
        user.activo = user_in.activo
        cambios["activo"] = user.activo
    if user_in.password is not None:
        user.password_hash = get_password_hash(user_in.password)
        cambios["password_actualizado"] = True

    await db.commit()
    await db.refresh(user)

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_admin.id,
        accion="ACTUALIZAR_USUARIO",
        entidad="usuario",
        entidad_id=str(user.id),
        detalle=cambios,
        request=request
    )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Baja lógica de usuario")
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    current_admin: Usuario = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    query = select(Usuario).where(Usuario.id == user_id)
    user = (await db.execute(query)).scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", "El usuario a dar de baja no existe.")

    if user.id == current_admin.id:
        raise ConflictError(
            codigo="AUTO_DESACTIVACION_PROHIBIDA",
            mensaje="No puedes desactivar tu propia cuenta de administrador."
        )

    user.activo = False
    await db.commit()

    await registrar_en_bitacora(
        db=db,
        usuario_id=current_admin.id,
        accion="DESACTIVAR_USUARIO",
        entidad="usuario",
        entidad_id=str(user.id),
        detalle={"email": user.email},
        request=request
    )
    return None
