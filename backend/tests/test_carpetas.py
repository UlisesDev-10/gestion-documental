import pytest
from httpx import AsyncClient
from app.models.usuario import Usuario


@pytest.mark.asyncio
async def test_crear_y_listar_carpetas(client: AsyncClient, editor_user: Usuario):
    # 1. Login como editor
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "editor@test.com", "password": "EditorPass123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Crear carpeta raíz
    crear_res = await client.post(
        "/api/v1/carpetas",
        headers=headers,
        json={"nombre": "Documentos Operativos"}
    )
    assert crear_res.status_code == 201
    carpeta_raiz = crear_res.json()
    assert carpeta_raiz["nombre"] == "Documentos Operativos"
    assert carpeta_raiz["carpeta_padre_id"] is None

    # 3. Crear subcarpeta
    sub_res = await client.post(
        "/api/v1/carpetas",
        headers=headers,
        json={
            "nombre": "2026",
            "carpeta_padre_id": carpeta_raiz["id"]
        }
    )
    assert sub_res.status_code == 201
    subcarpeta = sub_res.json()
    assert subcarpeta["carpeta_padre_id"] == carpeta_raiz["id"]

    # 4. Listar carpetas raíz
    list_res = await client.get("/api/v1/carpetas", headers=headers)
    assert list_res.status_code == 200
    raiz_items = list_res.json()
    assert any(c["id"] == carpeta_raiz["id"] for c in raiz_items)

    # 5. Listar subcarpetas
    sub_list_res = await client.get(
        f"/api/v1/carpetas?carpeta_padre_id={carpeta_raiz['id']}",
        headers=headers
    )
    assert sub_list_res.status_code == 200
    sub_items = sub_list_res.json()
    assert len(sub_items) >= 1
    assert sub_items[0]["nombre"] == "2026"


@pytest.mark.asyncio
async def test_lector_no_puede_crear_carpetas(client: AsyncClient, lector_user: Usuario):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "lector@test.com", "password": "LectorPass123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/carpetas",
        headers=headers,
        json={"nombre": "Carpeta No Autorizada"}
    )
    assert res.status_code == 403
