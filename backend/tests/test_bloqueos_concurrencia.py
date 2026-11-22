import io
import uuid
import pytest
from httpx import AsyncClient
from app.models.usuario import Usuario


@pytest.mark.asyncio
async def test_criterio_aceptacion_1_bloqueo_concurrente(
    client: AsyncClient,
    editor_user: Usuario,
    admin_user: Usuario
):
    # 1. Crear segundo editor
    # Login admin para crear editor 2
    login_admin = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    await client.post(
        "/api/v1/usuarios",
        headers=admin_headers,
        json={
            "email": "editor2@test.com",
            "password": "Editor2Pass123!",
            "nombre_completo": "Segundo Editor",
            "rol": "editor"
        }
    )

    # 2. Login de ambos editores
    res_ed1 = await client.post("/api/v1/auth/login", json={"email": "editor@test.com", "password": "EditorPass123!"})
    token_ed1 = res_ed1.json()["access_token"]
    headers_ed1 = {"Authorization": f"Bearer {token_ed1}"}

    res_ed2 = await client.post("/api/v1/auth/login", json={"email": "editor2@test.com", "password": "Editor2Pass123!"})
    token_ed2 = res_ed2.json()["access_token"]
    headers_ed2 = {"Authorization": f"Bearer {token_ed2}"}

    # 3. Editor 1 crea una carpeta y sube un archivo
    c_res = await client.post("/api/v1/carpetas", headers=headers_ed1, json={"nombre": "Proyectos"})
    carpeta_id = c_res.json()["id"]

    subir_res = await client.post(
        "/api/v1/archivos/subir",
        headers=headers_ed1,
        data={"carpeta_id": carpeta_id, "comentario": "Archivo base para pruebas de bloqueo"},
        files={"file": ("manual.docx", io.BytesIO(b"Contenido del manual"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    archivo_id = subir_res.json()["id"]

    # 4. Editor 1 adquiere el bloqueo exclusivo
    lock_res1 = await client.post(
        f"/api/v1/archivos/{archivo_id}/bloquear",
        headers=headers_ed1,
        json={"duracion_minutos": 30}
    )
    assert lock_res1.status_code == 200
    assert lock_res1.json()["bloqueado"] is True

    # 5. Escenario: Editor 2 intenta bloquear el mismo archivo -> debe recibir 409 Conflict
    lock_res2 = await client.post(
        f"/api/v1/archivos/{archivo_id}/bloquear",
        headers=headers_ed2,
        json={"duracion_minutos": 15}
    )
    assert lock_res2.status_code == 409
    data_conflict = lock_res2.json()
    assert data_conflict["error"]["codigo"] == "ARCHIVO_BLOQUEADO"

    # 6. Escenario: Editor 2 intenta subir una versión -> debe recibir 409 Conflict
    upload_res2 = await client.post(
        f"/api/v1/archivos/{archivo_id}/versiones",
        headers=headers_ed2,
        data={"comentario": "Intento de sobrescritura concurrente"},
        files={"file": ("manual.docx", io.BytesIO(b"Intento sobrescritura"), "application/octet-stream")}
    )
    assert upload_res2.status_code == 409

    # 7. Escenario: Editor 2 intenta descargar el archivo -> debe permitirse libremente (200 OK)
    download_res2 = await client.get(
        f"/api/v1/archivos/{archivo_id}/descargar",
        headers=headers_ed2
    )
    assert download_res2.status_code == 200
    assert download_res2.content == b"Contenido del manual"

    # 8. Escenario: Administrador ejecuta liberación forzada
    force_res = await client.post(
        f"/api/v1/archivos/{archivo_id}/forzar-desbloqueo",
        headers=admin_headers
    )
    assert force_res.status_code == 200
    assert force_res.json()["bloqueado"] is False

    # 9. Ahora Editor 2 ya puede bloquear o subir versión
    lock_after_force = await client.post(
        f"/api/v1/archivos/{archivo_id}/bloquear",
        headers=headers_ed2,
        json={"duracion_minutos": 10}
    )
    assert lock_after_force.status_code == 200
    assert lock_after_force.json()["bloqueado"] is True
