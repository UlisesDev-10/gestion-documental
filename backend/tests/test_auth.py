import pytest
from httpx import AsyncClient
from app.models.usuario import Usuario


@pytest.mark.asyncio
async def test_login_exitoso(client: AsyncClient, admin_user: Usuario):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["usuario"]["email"] == "admin@test.com"
    assert data["usuario"]["rol"] == "administrador"


@pytest.mark.asyncio
async def test_login_credenciales_incorrectas(client: AsyncClient, admin_user: Usuario):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "PasswordIncorrecto"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["codigo"] == "AUTENTICACION_FALLIDA"


@pytest.mark.asyncio
async def test_acceso_restringido_sin_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_crea_usuario_correctamente(client: AsyncClient, admin_user: Usuario):
    # 1. Login como admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    token = login_res.json()["access_token"]

    # 2. Crear usuario
    create_res = await client.post(
        "/api/v1/usuarios",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "nuevo.usuario@empresa.com",
            "password": "Password123!",
            "nombre_completo": "Nuevo Empleado",
            "rol": "editor"
        }
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["email"] == "nuevo.usuario@empresa.com"
    assert created_data["rol"] == "editor"
    assert created_data["activo"] is True


@pytest.mark.asyncio
async def test_lector_no_puede_crear_usuarios(client: AsyncClient, lector_user: Usuario):
    # 1. Login como lector
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "lector@test.com", "password": "LectorPass123!"}
    )
    token = login_res.json()["access_token"]

    # 2. Intento de crear usuario -> debe responder 403 Forbidden
    create_res = await client.post(
        "/api/v1/usuarios",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "infiltrado@empresa.com",
            "password": "Password123!",
            "nombre_completo": "Usuario Infiltrado",
            "rol": "administrador"
        }
    )
    assert create_res.status_code == 403
    data = create_res.json()
    assert data["error"]["codigo"] == "PERMISOS_INSUFICIENTES"
