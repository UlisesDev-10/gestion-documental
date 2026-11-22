import io
import pytest
from httpx import AsyncClient
from app.models.usuario import Usuario


@pytest.mark.asyncio
async def test_subida_versionado_y_restauracion_inmutable(client: AsyncClient, editor_user: Usuario):
    # 1. Login como editor
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "editor@test.com", "password": "EditorPass123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Crear carpeta para la prueba
    c_res = await client.post("/api/v1/carpetas", headers=headers, json={"nombre": "Contabilidad"})
    carpeta_id = c_res.json()["id"]

    # 3. Subir archivo inicial (v1)
    file_content_v1 = b"Contenido de prueba para la version 1"
    subir_res = await client.post(
        "/api/v1/archivos/subir",
        headers=headers,
        data={"carpeta_id": carpeta_id, "comentario": "Version inicial aprobada"},
        files={"file": ("balance.txt", io.BytesIO(file_content_v1), "text/plain")}
    )
    assert subir_res.status_code == 201
    archivo = subir_res.json()
    archivo_id = archivo["id"]
    v1_data = archivo["version_vigente"]
    assert v1_data["numero_version"] == 1
    assert v1_data["comentario"] == "Version inicial aprobada"
    sha_v1 = v1_data["sha256_hash"]

    # 4. Subir segunda versión (v2)
    file_content_v2 = b"Contenido modificado con cifras actualizadas para la version 2"
    v2_res = await client.post(
        f"/api/v1/archivos/{archivo_id}/versiones",
        headers=headers,
        data={"comentario": "Actualizacion de balance con cierre mensual"},
        files={"file": ("balance.txt", io.BytesIO(file_content_v2), "text/plain")}
    )
    assert v2_res.status_code == 201
    v2_data = v2_res.json()
    assert v2_data["numero_version"] == 2
    sha_v2 = v2_data["sha256_hash"]
    assert sha_v2 != sha_v1

    # 5. Consultar historial: debe mostrar exactamente 2 versiones consecutivas
    hist_res = await client.get(f"/api/v1/archivos/{archivo_id}/versiones", headers=headers)
    assert hist_res.status_code == 200
    historial = hist_res.json()
    assert len(historial) == 2
    assert historial[0]["numero_version"] == 2
    assert historial[0]["es_vigente"] is True
    assert historial[1]["numero_version"] == 1
    assert historial[1]["es_vigente"] is False

    # 6. Criterio de Aceptación 4: Restaurar versión 1
    # Debe generar la versión 3 con el mismo contenido/hash de v1, sin borrar v1 ni v2
    v1_id = historial[1]["id"]
    restaurar_res = await client.post(
        f"/api/v1/archivos/{archivo_id}/versiones/{v1_id}/restaurar",
        headers=headers,
        json={"comentario": "Restauracion voluntaria a la version 1"}
    )
    assert restaurar_res.status_code == 201
    v3_data = restaurar_res.json()
    assert v3_data["numero_version"] == 3
    assert v3_data["sha256_hash"] == sha_v1  # El contenido coincide con v1
    assert v3_data["comentario"] == "Restauracion voluntaria a la version 1"

    # 7. Verificar que el historial ahora tiene 3 versiones inalteradas
    hist_final_res = await client.get(f"/api/v1/archivos/{archivo_id}/versiones", headers=headers)
    hist_final = hist_final_res.json()
    assert len(hist_final) == 3
    assert hist_final[0]["numero_version"] == 3
    assert hist_final[1]["numero_version"] == 2
    assert hist_final[2]["numero_version"] == 1

    # 8. Descargar versión vigente (debe ser la v3 que tiene el contenido de v1)
    descarga_res = await client.get(f"/api/v1/archivos/{archivo_id}/descargar", headers=headers)
    assert descarga_res.status_code == 200
    assert descarga_res.content == file_content_v1
    assert descarga_res.headers["X-Integrity-SHA256"] == sha_v1
