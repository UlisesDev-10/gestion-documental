import asyncio
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.usuario import RolUsuario, Usuario

# Base de datos SQLite en memoria para tests aislados
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def admin_user(db_session: AsyncSession):
    user = Usuario(
        id=uuid.uuid4(),
        email="admin@test.com",
        password_hash=get_password_hash("AdminPass123!"),
        nombre_completo="Administrador Test",
        rol=RolUsuario.ADMINISTRADOR,
        activo=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def editor_user(db_session: AsyncSession):
    user = Usuario(
        id=uuid.uuid4(),
        email="editor@test.com",
        password_hash=get_password_hash("EditorPass123!"),
        nombre_completo="Editor Test",
        rol=RolUsuario.EDITOR,
        activo=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def lector_user(db_session: AsyncSession):
    user = Usuario(
        id=uuid.uuid4(),
        email="lector@test.com",
        password_hash=get_password_hash("LectorPass123!"),
        nombre_completo="Lector Test",
        rol=RolUsuario.LECTOR,
        activo=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
