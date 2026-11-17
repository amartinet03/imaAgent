import requests
import json
import os
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=== INICIANDO SUITE DE TESTS DE SEGURIDAD Y ENDPOINTS ===")
    
    # 1. Health check
    print("\n[1] Probando Health Check...")
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Error en health: {r.status_code}"
    data = r.json()
    assert data["status"] == "ok"
    assert data["database"] == "postgres"
    print("  -> OK: Health check activo y conectado a PostgreSQL.")

    # 2. Login con credenciales incorrectas (Seguridad)
    print("\n[2] Probando Seguridad: Rechazo de credenciales inválidas...")
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert r.status_code == 401, f"Fallo de seguridad: {r.status_code}"
    print("  -> OK: Credenciales inválidas rechazadas con código 401.")

    # 3. Login con credenciales correctas
    print("\n[3] Probando Login de Administrador...")
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "Ima2026!"})
    assert r.status_code == 200, f"Error en login: {r.status_code}"
    token_data = r.json()
    assert "token" in token_data
    token = token_data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  -> OK: Login exitoso. Token generado.")

    # 4. Estadísticas del Dashboard
    print("\n[4] Probando Estadísticas del Dashboard (/api/tenders/stats)...")
    r = requests.get(f"{BASE_URL}/api/tenders/stats", headers=headers)
    assert r.status_code == 200
    stats = r.json()
    assert "total" in stats and "procesando" in stats and "completadas" in stats
    print(f"  -> OK: Estadísticas recuperadas: {stats}")

    # 5. Listado de Licitaciones
    print("\n[5] Probando Listado de Licitaciones (/api/tenders)...")
    r = requests.get(f"{BASE_URL}/api/tenders", headers=headers)
    assert r.status_code == 200
    tenders = r.json()
    assert isinstance(tenders, list)
    print(f"  -> OK: Listado de licitaciones recuperado ({len(tenders)} encontradas).")

    # 6. Radar de Licitaciones: Portales y Palabras Clave
    print("\n[6] Probando Radar de Licitaciones (Portales y Keywords)...")
    r_portals = requests.get(f"{BASE_URL}/api/radar/portals", headers=headers)
    assert r_portals.status_code == 200
    portals = r_portals.json()
    assert len(portals) >= 2, "Deben existir al menos los 2 portales por defecto"
    print(f"  -> OK: {len(portals)} portales monitoreados activos (NA-SA, ARSAT, etc.).")

    r_kw = requests.get(f"{BASE_URL}/api/radar/keywords", headers=headers)
    assert r_kw.status_code == 200
    keywords = r_kw.json()
    assert len(keywords) >= 10, "Deben existir al menos las 10 palabras clave por defecto"
    print(f"  -> OK: {len(keywords)} palabras clave activas en PostgreSQL.")

    # 7. Crear y eliminar palabra clave de prueba
    print("\n[7] Probando Creación y Borrado de Palabra Clave...")
    r_add_kw = requests.post(f"{BASE_URL}/api/radar/keywords", json={"keyword": "test_mantenimiento_valvulas"}, headers=headers)
    assert r_add_kw.status_code == 200
    kw_id = r_add_kw.json().get("id")
    if kw_id:
        r_del_kw = requests.delete(f"{BASE_URL}/api/radar/keywords/{kw_id}", headers=headers)
        assert r_del_kw.status_code == 200
    print("  -> OK: Creación y borrado de keywords verificado.")

    # 8. Estado del Daemon de Automatización
    print("\n[8] Probando Estado del Daemon de Automatización...")
    r_daemon = requests.get(f"{BASE_URL}/api/radar/daemon", headers=headers)
    assert r_daemon.status_code == 200
    daemon_data = r_daemon.json()
    assert "active" in daemon_data and "settings" in daemon_data
    print(f"  -> OK: Configuración del Daemon recuperada: {daemon_data}")

    # 9. Crear Licitación de Prueba con documento simulado
    print("\n[9] Probando Creación de Licitación con Archivo...")
    test_file_content = b"PLIEGO TECNICO DE LICITACION DE PRUEBA - IMA SERVICIOS INDUSTRIALES"
    files = [("files", ("pliego_prueba.txt", test_file_content, "text/plain"))]
    data = {"name": "Licitación Test de Integración"}
    r_create = requests.post(f"{BASE_URL}/api/tenders", data=data, files=files, headers=headers)
    assert r_create.status_code == 200, f"Error al crear: {r_create.text}"
    created_tender = r_create.json()
    tender_id = created_tender["tender_id"]
    print(f"  -> OK: Licitación creada exitosamente con ID #{tender_id}.")

    # 10. Consultar detalle de la Licitación creada
    print("\n[10] Probando Consulta de Detalle de Licitación...")
    r_detail = requests.get(f"{BASE_URL}/api/tenders/{tender_id}", headers=headers)
    assert r_detail.status_code == 200
    detail = r_detail.json()
    assert detail["id"] == tender_id
    assert detail["name"] == "Licitación Test de Integración"
    print(f"  -> OK: Detalle recuperado correctamente. Estado: {detail['status']}.")

    # 11. Limpieza de Licitación de prueba
    print("\n[11] Limpiando licitación de prueba...")
    # Solo eliminar si no está bloqueada por procesamiento activo
    r_del = requests.delete(f"{BASE_URL}/api/tenders/{tender_id}", headers=headers)
    if r_del.status_code == 200:
        print("  -> OK: Licitación de prueba eliminada.")
    else:
        print(f"  -> Nota: {r_del.json().get('detail')}")

    print("\n" + "="*50)
    print("[EXITO TOTAL] TODOS LOS TESTS PASARON CORRECTAMENTE (11/11)")
    print("="*50)

if __name__ == "__main__":
    run_tests()
