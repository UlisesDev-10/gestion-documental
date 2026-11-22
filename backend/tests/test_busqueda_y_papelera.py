import io
import pytest
from httpx import AsyncClient
from app.models.usuario import Usuario


@pytest.mark.asyncio
async def test_busqueda_papelera_y_criterios_seguridad(
    client: AsyncClient,
    editor_user: Usuario,
    lector_user: Usuario,
    admin_user: Usuario
):
    # 1. Login editor
    login_ed = await client.post("/api/v1/auth/login", json={"email": "editor@test.com", "password": "EditorPass123!"})
    token_ed = login_ed.json()["access_token"]
    headers_ed = {"Authorization": f"Bearer {token_ed}"}

    # 2. Login lector
    login_lec = await client.post("/api/v1/auth/login", json={"email": "lector@test.com", "password": "LectorPass123!"})
    token_lec = login_lec.json()["access_token"]
    headers_lec = {"Authorization": f"Bearer {token_lec}"}

    # 3. Login admin
    login_adm = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "AdminPass123!"})
    token_adm = login_adm.json()["access_token"]
    headers_adm = {"Authorization": f"Bearer {token_adm}"}

    # 4. Crear carpeta y subir 2 archivos con distintas extensiones
    c_res = await client.post("/api/v1/carpetas", headers=headers_ed, json={"nombre": "Reportes"})
    carpeta_id = c_res.json()["id"]

    sub1 = await client.post(
        "/api/v1/archivos/subir",
        headers=headers_ed,
        data={"carpeta_id": carpeta_id, "comentario": "Informe financiero anual"},
        files={"file": ("informe_anual_2026.pdf", io.BytesIO(b"%PDF-1.4 informe anual"), "application/pdf")}
    )
    archivo_pdf_id = sub1.json()["id"]

    sub2 = await client.post(
        "/api/v1/archivos/subir",
        headers=headers_ed,
        data={"carpeta_id": carpeta_id, "comentario": "Calculo de impuestos"},
        files={"file": ("calculo_impuestos.xlsx", io.BytesIO(b"hoja de calculo"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    archivo_xlsx_id = sub2.json()["id"]

    # 5. Prueba de Búsqueda: Buscar por extensión 'pdf'
    search_pdf = await client.get("/api/v1/busqueda?extension=pdf", headers=headers_lec)
    assert search_pdf.status_code == 200
    pdf_results = search_pdf.json()["elementos"]
    assert any(item["nombre"] == "informe_anual_2026.pdf" for item in pdf_results)
    assert not any(item["nombre"] == "calculo_impuestos.xlsx" for item in pdf_results)

    # 6. Prueba de Búsqueda: Buscar por nombre 'impuestos'
    search_name = await client.get("/api/v1/busqueda?q=impuestos", headers=headers_lec)
    assert search_name.status_code == 200
    name_results = search_name.json()["elementos"]
    assert any(item["nombre"] == "calculo_impuestos.xlsx" for item in name_results)

    # 7. Criterio de Aceptación 5: Seguridad de Lector
    # Lector intenta eliminar un archivo -> debe responder 403 Forbidden
    del_forbidden = await client.delete(f"/api/v1/archivos/{archivo_pdf_id}", headers=headers_lec)
    assert del_forbidden.status_code == 403
    assert del_forbidden.json()["error"]["codigo"] == "PERMISOS_INSUFICIENTES"

    # 8. Criterio de Aceptación 6: Ciclo de vida en papelera
    # Editor elimina archivo -> va a papelera
    del_ok = await client.delete(f"/api/v1/archivos/{archivo_pdf_id}", headers=headers_ed)
    assert del_ok.status_code == 204

    # Verificar que ya no aparece en el listado activo de la carpeta
    list_active = await client.get(f"/api/v1/archivos?carpeta_id={carpeta_id}", headers=headers_ed)
    assert not any(a["id"] == archivo_pdf_id for a in list_active.json())

    # Consultar papelera -> debe aparecer
    trash_res = await client.get("/api/v1/papelera", headers=headers_ed)
    assert trash_res.status_code == 200
    trash_items = trash_res.json()["elementos"]
    assert any(item["id"] == archivo_pdf_id for item in trash_items)

    # Restaurar archivo desde papelera
    restore_trash = await client.post(f"/api/v1/papelera/archivos/{archivo_pdf_id}/restaurar", headers=headers_ed)
    assert restore_trash.status_code == 200

    # Verificar que vuelve a estar activo con su versión intacta
    list_active_again = await client.get(f"/api/v1/archivos?carpeta_id={carpeta_id}", headers=headers_ed)
    assert any(a["id"] == archivo_pdf_id for a in list_active_again.json())

    # 9. Bitácora de Auditoría: El administrador consulta los registros
    audit_res = await client.get("/api/v1/bitacora", headers=headers_adm)
    assert audit_res.status_code == 200
    logs = audit_res.json()["items"]
    assert len(logs) > 0
    acciones_registradas = [log["accion"] for log in logs]
    assert "SUBIR_ARCHIVO" in acciones_registradas
    assert "ENVIAR_PAPELERA_ARCHIVO" in acciones_registradas
    assert "RESTAURAR_PAPELERA_ARCHIVO" in acciones_registradas
