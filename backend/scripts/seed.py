"""
seed.py — Datos de ejemplo iniciales para la Fase 1.

Idempotente: se puede ejecutar varias veces sin crear duplicados.

Uso (desde la carpeta backend/):
    py -3.12 scripts/seed.py

O desde la raíz del repositorio:
    py -3.12 backend/scripts/seed.py
"""
import asyncio
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Permite importar app.* sin instalar el paquete si se ejecuta directamente
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../backend/
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, engine
from app.core.security import get_password_hash
from app.models import Base  # noqa: F401 — asegura que todos los modelos se registren
from app.models.carpeta import Carpeta
from app.models.permiso import NivelAcceso, Permiso
from app.models.usuario import RolUsuario, Usuario

# ---------------------------------------------------------------------------
# Datos de semilla
# ---------------------------------------------------------------------------

USUARIOS_SEMILLA = [
    {
        "email": "admin@empresa.com",
        "password": "Admin123!",
        "nombre_completo": "Administrador del Sistema",
        "rol": RolUsuario.ADMINISTRADOR,
    },
    {
        "email": "editor@empresa.com",
        "password": "Editor123!",
        "nombre_completo": "Editor de Documentos",
        "rol": RolUsuario.EDITOR,
    },
    {
        "email": "revisor@empresa.com",
        "password": "Revisor123!",
        "nombre_completo": "Revisor de Contenidos",
        "rol": RolUsuario.REVISOR,
    },
    {
        "email": "lector@empresa.com",
        "password": "Lector123!",
        "nombre_completo": "Lector General",
        "rol": RolUsuario.LECTOR,
    },
]

CARPETAS_SEMILLA = ["Operaciones", "Recursos Humanos"]

# Permisos: (rol, nivel_acceso) aplicados a cada carpeta raíz
PERMISOS_POR_ROL = [
    (RolUsuario.EDITOR, NivelAcceso.EDICION),
    (RolUsuario.REVISOR, NivelAcceso.LECTURA),
    (RolUsuario.LECTOR, NivelAcceso.LECTURA),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_or_create_usuario(session: AsyncSession, data: dict) -> Usuario:
    """Devuelve el usuario existente o lo crea. No modifica si ya existe."""
    result = await session.execute(
        select(Usuario).where(Usuario.email == data["email"])
    )
    usuario = result.scalar_one_or_none()

    if usuario is None:
        usuario = Usuario(
            email=data["email"],
            password_hash=get_password_hash(data["password"]),
            nombre_completo=data["nombre_completo"],
            rol=data["rol"],
            activo=True,
        )
        session.add(usuario)
        await session.flush()  # obtiene el ID sin cerrar la transacción
        print(f"  ✔ Usuario creado: {data['email']} [{data['rol'].value}]")
    else:
        print(f"  · Usuario ya existe: {data['email']} — sin cambios")

    return usuario


async def _get_or_create_carpeta(
    session: AsyncSession, nombre: str, creado_por_id
) -> Carpeta:
    """Devuelve la carpeta raíz existente con ese nombre o la crea."""
    result = await session.execute(
        select(Carpeta).where(
            Carpeta.nombre == nombre,
            Carpeta.carpeta_padre_id.is_(None),
            Carpeta.en_papelera.is_(False),
        )
    )
    carpeta = result.scalar_one_or_none()

    if carpeta is None:
        carpeta = Carpeta(
            nombre=nombre,
            carpeta_padre_id=None,
            creado_por=creado_por_id,
            en_papelera=False,
        )
        session.add(carpeta)
        await session.flush()
        print(f"  ✔ Carpeta creada: «{nombre}»")
    else:
        print(f"  · Carpeta ya existe: «{nombre}» — sin cambios")

    return carpeta


async def _get_or_create_permiso(
    session: AsyncSession,
    carpeta_id,
    rol_tipo: RolUsuario,
    nivel_acceso: NivelAcceso,
) -> None:
    """Crea el permiso de rol si no existe ya para esa carpeta."""
    result = await session.execute(
        select(Permiso).where(
            Permiso.carpeta_id == carpeta_id,
            Permiso.rol_tipo == rol_tipo,
            Permiso.usuario_id.is_(None),
        )
    )
    permiso = result.scalar_one_or_none()

    if permiso is None:
        permiso = Permiso(
            carpeta_id=carpeta_id,
            usuario_id=None,          # permiso aplicado al rol completo
            rol_tipo=rol_tipo,
            nivel_acceso=nivel_acceso,
        )
        session.add(permiso)
        print(
            f"    ✔ Permiso: rol={rol_tipo.value} → {nivel_acceso.value}"
        )
    else:
        print(
            f"    · Permiso ya existe: rol={rol_tipo.value} → sin cambios"
        )


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------


async def run_seed() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            print("\n── Usuarios ─────────────────────────────────────────")
            usuarios: dict[str, Usuario] = {}
            for data in USUARIOS_SEMILLA:
                u = await _get_or_create_usuario(session, data)
                usuarios[data["rol"].value] = u

            admin = usuarios[RolUsuario.ADMINISTRADOR.value]

            print("\n── Carpetas raíz ────────────────────────────────────")
            carpetas = []
            for nombre in CARPETAS_SEMILLA:
                c = await _get_or_create_carpeta(session, nombre, admin.id)
                carpetas.append(c)

            print("\n── Permisos de rol ──────────────────────────────────")
            for carpeta in carpetas:
                print(f"  Carpeta: «{carpeta.nombre}»")
                for rol_tipo, nivel_acceso in PERMISOS_POR_ROL:
                    await _get_or_create_permiso(
                        session, carpeta.id, rol_tipo, nivel_acceso
                    )

        # La transacción se confirma automáticamente al salir del bloque begin()

    await engine.dispose()
    print("\n✅ Semilla completada con éxito.\n")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(run_seed())
