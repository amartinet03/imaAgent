import os
import sys
import glob
import re
import shutil
import json
import time
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"), override=True)

from src.db.models import (
    init_db,
    verify_user_credentials,
    update_user_password,
    get_all_tenders,
    get_tender,
    create_tender,
    delete_tender,
    update_tender_status,
    update_tender_progress,
    update_tender_parsed_data,
    add_message,
    get_messages,
    get_monitored_portals,
    add_monitored_portal,
    delete_monitored_portal,
    toggle_monitored_portal,
    get_monitored_keywords,
    add_monitored_keyword,
    delete_monitored_keyword,
    get_pending_opportunities,
    get_all_opportunities,
    update_opportunity_status,
    delete_radar_opportunity,
    get_daemon_settings,
    set_daemon_setting,
    is_daemon_active,
    set_daemon_active
)

from src.background_worker import process_tender
from src.core.chat_worker import is_chat_job_running, start_chat_background_job, get_chat_job_info
from src.outputs.word_generator import WordGenerator
from src.outputs.query_generator import QueryGenerator
from src.outputs.excel_generator import ExcelGenerator

app = FastAPI(
    title="IMA Agent API",
    description="Backend FastAPI para el sistema de análisis inteligente de licitaciones de IMA Servicios Industriales",
    version="3.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para resolver compatibilidad de rutas con balanceadores y proxies (DigitalOcean App Platform)
@app.middleware("http")
async def ensure_api_prefix_compatibility(request: Request, call_next):
    path = request.scope.get("path", "")
    # Caso 1: El proxy concatenó sin barra divisoria (ej: /apiauth/login -> /api/auth/login)
    if path.startswith("/api") and not path.startswith("/api/"):
        request.scope["path"] = f"/api/{path[4:].lstrip('/')}"
    # Caso 2: El proxy recortó /api/ completamente (ej: /auth/login -> /api/auth/login)
    elif not (path.startswith("/api/") or path.startswith("/data") or path.startswith("/docs") or path.startswith("/openapi.json") or path.startswith("/redoc")):
        request.scope["path"] = f"/api/{path.lstrip('/')}"
    # Caso 3: Lo mismo para /data si viniera sin barra (ej: /datatenders -> /data/tenders)
    elif path.startswith("/data") and not path.startswith("/data/"):
        request.scope["path"] = f"/data/{path[5:].lstrip('/')}"
        
    return await call_next(request)

# Ensure data and template directories exist
DATA_DIR = os.path.join(backend_dir, "data")
TENDERS_DIR = os.path.join(DATA_DIR, "tenders")
TEMPLATES_DIR = os.path.join(backend_dir, "templates")
os.makedirs(TENDERS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Mount /data for downloading documents
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

@app.on_event("startup")
def on_startup():
    print("=== [IMA AGENT API] Inicializando Base de Datos en Startup ===")
    init_db()
    from src.core.radar_scheduler import start_radar_scheduler
    start_radar_scheduler()
    from src.daemon import start_email_daemon
    start_email_daemon()
    print("=== [IMA AGENT API] Servidor listo y escuchando ===")


# ============================================================================
# 1. AUTENTICACIÓN
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordChangeRequest(BaseModel):
    username: str
    current_password: str
    new_password: str

@app.post("/api/auth/login")
def login(req: LoginRequest):
    if verify_user_credentials(req.username, req.password):
        # Token simple para sesión segura
        import base64
        token = base64.b64encode(req.username.encode("utf-8")).decode("utf-8")
        return {
            "status": "success",
            "token": token,
            "username": req.username
        }
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

@app.post("/api/auth/change-password")
def change_password(req: PasswordChangeRequest):
    if not verify_user_credentials(req.username, req.current_password):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres.")
    update_user_password(req.username, req.new_password)
    return {"status": "success", "message": "Contraseña actualizada exitosamente"}


# ============================================================================
# 2. DASHBOARD Y LICITACIONES (CRUD)
# ============================================================================

@app.get("/api/tenders/stats")
def get_stats():
    tenders = get_all_tenders()
    total = len(tenders)
    procesando = sum(1 for t in tenders if t.get('status') == 'PROCESANDO')
    completadas = sum(1 for t in tenders if t.get('status') == 'COMPLETADO')

    now = datetime.now()
    semana_pasada = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    nuevas_esta_semana = sum(1 for t in tenders if str(t.get('created_at', '')) >= semana_pasada)

    return {
        "total": total,
        "procesando": procesando,
        "completadas": completadas,
        "nuevas_esta_semana": nuevas_esta_semana
    }

@app.get("/api/tenders")
def list_tenders():
    tenders = get_all_tenders()
    for t in tenders:
        if t.get('progress') is None:
            if t.get('status') == 'COMPLETADO':
                t['progress'] = 100
            elif t.get('status') == 'PROCESANDO':
                t['progress'] = 45
            else:
                t['progress'] = 0
    return tenders

@app.post("/api/tenders")
def create_new_tender(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    files: List[UploadFile] = File(...)
):
    if not name or not files:
        raise HTTPException(status_code=400, detail="Se requiere el nombre y al menos un archivo.")

    tender_id = create_tender(name)
    tender_docs_dir = os.path.join(TENDERS_DIR, str(tender_id), "docs")
    os.makedirs(tender_docs_dir, exist_ok=True)

    # Guardar archivos subidos
    for file in files:
        safe_name = os.path.basename(file.filename)
        safe_name = re.sub(r'[^a-zA-Z0-9_.\-áéíóúÁÉÍÓÚñÑ ]', '_', safe_name)
        dest_path = os.path.join(tender_docs_dir, safe_name)
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    # Disparar background worker
    background_tasks.add_task(process_tender, tender_id)

    return {
        "status": "success",
        "tender_id": tender_id,
        "name": name,
        "message": "Licitación creada. Procesamiento en segundo plano iniciado."
    }

@app.get("/api/tenders/{tender_id}")
def get_tender_detail(tender_id: int):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")
    
    # Check if chat worker is running
    tender["is_chat_running"] = is_chat_job_running(tender_id)
    tender["chat_job_info"] = get_chat_job_info(tender_id, "OT") or get_chat_job_info(tender_id, "CONSULTAS")
    return tender

@app.delete("/api/tenders/{tender_id}")
def remove_tender(tender_id: int):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")
    if tender.get("status") == "PROCESANDO":
        raise HTTPException(status_code=400, detail="No se puede borrar una licitación mientras se procesa.")
    
    delete_tender(tender_id)
    shutil.rmtree(os.path.join(TENDERS_DIR, str(tender_id)), ignore_errors=True)
    return {"status": "success", "message": f"Licitación {tender_id} eliminada."}


# ============================================================================
# 3. PESTAÑA DOCUMENTOS
# ============================================================================

@app.get("/api/tenders/{tender_id}/documents")
def list_tender_documents(tender_id: int):
    docs_dir = os.path.join(TENDERS_DIR, str(tender_id), "docs")
    if not os.path.exists(docs_dir):
        return []
    
    docs_list = []
    for fname in os.listdir(docs_dir):
        fpath = os.path.join(docs_dir, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            size_kb = round(stat.st_size / 1024, 1)
            ext = os.path.splitext(fname)[1].lower()
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
            docs_list.append({
                "name": fname,
                "size_kb": size_kb,
                "extension": ext,
                "modified": mtime,
                "download_url": f"/data/tenders/{tender_id}/docs/{fname}"
            })
    return docs_list

@app.post("/api/tenders/{tender_id}/documents/upload")
def upload_tender_documents(
    tender_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    auto_reanalyze: bool = Form(False)
):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")
        
    docs_dir = os.path.join(TENDERS_DIR, str(tender_id), "docs")
    os.makedirs(docs_dir, exist_ok=True)

    for file in files:
        safe_name = os.path.basename(file.filename)
        safe_name = re.sub(r'[^a-zA-Z0-9_.\-áéíóúÁÉÍÓÚñÑ ]', '_', safe_name)
        dest_path = os.path.join(docs_dir, safe_name)
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    if auto_reanalyze:
        update_tender_status(tender_id, "PROCESANDO")
        update_tender_progress(tender_id, 0, "Iniciando re-análisis integral...")
        background_tasks.add_task(process_tender, tender_id)

    return {"status": "success", "message": f"{len(files)} archivo(s) guardado(s)."}

@app.post("/api/tenders/{tender_id}/reanalyze")
def trigger_reanalysis(tender_id: int, background_tasks: BackgroundTasks):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")
    if tender.get("status") == "PROCESANDO":
        raise HTTPException(status_code=400, detail="Ya se encuentra un análisis en curso.")

    update_tender_status(tender_id, "PROCESANDO")
    update_tender_progress(tender_id, 5, "Iniciando El Show (Análisis Integral)...")
    background_tasks.add_task(process_tender, tender_id)
    return {"status": "success", "message": "Análisis integral ('El Show') iniciado en segundo plano."}


# ============================================================================
# 4. PESTAÑA RFI / CONSULTAS AL PLIEGO
# ============================================================================

class RFIUpdateRequest(BaseModel):
    inconsistencias: list
    consultas_generales: list

@app.get("/api/tenders/{tender_id}/rfi")
def get_rfi_data(tender_id: int):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")
    
    parsed_data = tender.get("parsed_data") or {}
    outputs_dir = os.path.join(TENDERS_DIR, str(tender_id), "outputs")
    rfi_files = glob.glob(os.path.join(outputs_dir, "Consultas_*.docx"))
    
    versions = []
    for fpath in sorted(rfi_files):
        fname = os.path.basename(fpath)
        stat = os.stat(fpath)
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
        match = re.search(r'REV(\d+)', fname, re.IGNORECASE)
        rev_tag = f"REV{match.group(1)}" if match else "REV00"
        versions.append({
            "name": fname,
            "revision": rev_tag,
            "date": mtime,
            "download_url": f"/data/tenders/{tender_id}/outputs/{fname}"
        })

    return {
        "inconsistencias": parsed_data.get("inconsistencias", []),
        "consultas_generales": parsed_data.get("consultas_generales", []),
        "versions": versions
    }

@app.put("/api/tenders/{tender_id}/rfi")
def update_rfi_data(tender_id: int, req: RFIUpdateRequest):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")

    parsed_data = tender.get("parsed_data") or {}
    parsed_data["inconsistencias"] = req.inconsistencias
    parsed_data["consultas_generales"] = req.consultas_generales
    update_tender_parsed_data(tender_id, parsed_data)

    # Regenerar documento Word de consultas con número de revisión nuevo
    outputs_dir = os.path.join(TENDERS_DIR, str(tender_id), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    rfi_template = os.path.join(TEMPLATES_DIR, "Consultas_Pliego_PAMPA_Obras_Civiles_Menores_PGSM.docx")

    cliente = parsed_data.get("metadata", {}).get("cliente", f"Licitacion_{tender_id}")
    safe_cliente = re.sub(r'[^A-Za-z0-9]+', '_', str(cliente))
    existing_files = glob.glob(os.path.join(outputs_dir, "Consultas_*.docx"))
    rev_num = len(existing_files)
    rfi_name = f"Consultas_Pliego_{safe_cliente}_REV{rev_num:02d}.docx"
    rfi_path = os.path.join(outputs_dir, rfi_name)

    try:
        QueryGenerator().generate_docx_from_json(parsed_data, rfi_template, rfi_path)
    except Exception as e:
        print(f"[RFI Warning] No se pudo regenerar Word de consultas: {e}")

    return {"status": "success", "message": "Consultas e inconsistencias actualizadas.", "new_doc": rfi_name}


# ============================================================================
# 5. PESTAÑA OFERTA TÉCNICA (OT)
# ============================================================================

@app.get("/api/tenders/{tender_id}/ot")
def get_ot_data(tender_id: int):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")

    parsed_data = tender.get("parsed_data") or {}
    metadata = parsed_data.get("metadata", {})
    outputs_dir = os.path.join(TENDERS_DIR, str(tender_id), "outputs")
    ot_files = glob.glob(os.path.join(outputs_dir, "OT_*.docx"))

    versions = []
    for fpath in sorted(ot_files):
        fname = os.path.basename(fpath)
        stat = os.stat(fpath)
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
        match = re.search(r'REV(\d+)', fname, re.IGNORECASE)
        rev_tag = f"REV{match.group(1)}" if match else "REV00"
        versions.append({
            "name": fname,
            "revision": rev_tag,
            "date": mtime,
            "download_url": f"/data/tenders/{tender_id}/outputs/{fname}"
        })

    return {
        "metadata": {
            "cliente": metadata.get("cliente", "N/A"),
            "planta": metadata.get("planta", "N/A"),
            "proceso": metadata.get("proceso", "N/A"),
            "responsable": "Sebastien Martinet",
            "nombre_pliego": metadata.get("nombre_pliego", "N/A"),
            "moneda": metadata.get("moneda", "No especificada"),
        },
        "versions": versions,
        "is_generating": is_chat_job_running(tender_id, "OT")
    }


# ============================================================================
# 6. ASISTENTE IA (CHAT EN VIVO Y MODIFICACIÓN DE VERSIONES)
# ============================================================================

class ChatMessageRequest(BaseModel):
    prompt: str
    chat_type: str = "OT"

@app.get("/api/tenders/{tender_id}/chat")
def get_chat_history(tender_id: int, chat_type: str = "OT"):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")

    messages = get_messages(tender_id, chat_type=chat_type)
    if not messages:
        header_title = "Oferta Técnica (OT)" if chat_type == "OT" else "Consultas al Pliego (RFI)"
        initial_msg = f"¡Hola! Soy tu asistente de IA. He extraído la información para la sección de {header_title}. ¿Hay algo que desees ajustar antes de generar una nueva versión?"
        add_message(tender_id, "assistant", initial_msg, chat_type=chat_type)
        messages = get_messages(tender_id, chat_type=chat_type)

    return {
        "messages": messages,
        "is_job_running": is_chat_job_running(tender_id, chat_type),
        "job_info": get_chat_job_info(tender_id, chat_type)
    }

@app.post("/api/tenders/{tender_id}/chat")
def post_chat_message(tender_id: int, req: ChatMessageRequest):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")
    if is_chat_job_running(tender_id, req.chat_type):
        raise HTTPException(status_code=400, detail="Ya hay una tarea de IA en ejecución para esta sección.")

    add_message(tender_id, "user", req.prompt, chat_type=req.chat_type)
    started = start_chat_background_job(tender_id, req.chat_type, req.prompt)
    if not started:
        raise HTTPException(status_code=500, detail="No se pudo iniciar el proceso de IA en segundo plano.")

    return {
        "status": "success",
        "message": "Instrucción enviada a la IA. La nueva versión se está ensamblando en segundo plano."
    }


# ============================================================================
# 7. PESTAÑA OFERTA ECONÓMICA
# ============================================================================

@app.get("/api/tenders/{tender_id}/eco")
def get_eco_data(tender_id: int):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")

    parsed_data = tender.get("parsed_data") or {}
    outputs_dir = os.path.join(TENDERS_DIR, str(tender_id), "outputs")
    excel_files = glob.glob(os.path.join(outputs_dir, "Costos_*.xlsx")) + glob.glob(os.path.join(outputs_dir, "*.xlsx"))
    
    versions = []
    for fpath in sorted(excel_files):
        fname = os.path.basename(fpath)
        if fname.startswith("TEMP_"):
            continue
        stat = os.stat(fpath)
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
        versions.append({
            "name": fname,
            "date": mtime,
            "download_url": f"/data/tenders/{tender_id}/outputs/{fname}"
        })

    return {
        "moneda": parsed_data.get("metadata", {}).get("moneda", "No especificada"),
        "formato": "Excel Estándar IMA",
        "versions": versions
    }

@app.post("/api/tenders/{tender_id}/eco/generate")
def generate_base_cost_excel(tender_id: int):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")

    outputs_dir = os.path.join(TENDERS_DIR, str(tender_id), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    template_path = os.path.join(TEMPLATES_DIR, "plantilla_costeo.xlsx")
    
    parsed_data = tender.get("parsed_data") or {}
    cliente = parsed_data.get("metadata", {}).get("cliente", f"Licitacion_{tender_id}")
    safe_cliente = re.sub(r'[^A-Za-z0-9]+', '_', str(cliente))
    
    out_name = f"Costos_{tender_id}_{safe_cliente}_REV00.xlsx"
    out_path = os.path.join(outputs_dir, out_name)

    generator = ExcelGenerator()
    generator.generate_cost_excel({"parsed_data": parsed_data}, template_path, out_path)

    return {"status": "success", "file": out_name, "download_url": f"/data/tenders/{tender_id}/outputs/{out_name}"}

@app.post("/api/tenders/{tender_id}/eco/validate")
def validate_cost_excel(tender_id: int, file: UploadFile = File(...)):
    tender = get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")

    outputs_dir = os.path.join(TENDERS_DIR, str(tender_id), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    safe_base = re.sub(r'[^a-zA-Z0-9_.\-]', '_', file.filename)
    temp_path = os.path.join(outputs_dir, f"TEMP_{safe_base}")

    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        from src.core.analyzer import get_anthropic_api_key
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model_name=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            anthropic_api_key=get_anthropic_api_key()
        )
        generator = ExcelGenerator(llm_client=llm)
        report = generator.validate_cost_excel({"parsed_data": tender.get("parsed_data", {})}, temp_path)
        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al validar archivo de costos: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ============================================================================
# 8. RADAR WEB Y DAEMON DE AUTOMATIZACIÓN
# ============================================================================

@app.get("/api/radar/opportunities")
def list_opportunities():
    return get_all_opportunities()

@app.get("/api/radar/opportunities/pending")
def list_pending_opportunities():
    return get_pending_opportunities()

def try_download_portal_attachments(url: str, dest_dir: str, max_files: int = 5) -> List[str]:
    """
    Inspecciona la URL oficial de la licitación e intenta descargar de forma automática
    los pliegos o anexos técnicos (.pdf, .docx, .xlsx, .xls) públicos enlazados.
    """
    downloaded = []
    if not url or not url.startswith("http"):
        return downloaded
    try:
        import requests
        import urllib.parse
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        res = requests.get(url, headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            pattern = r'href=["\']([^"\']+\.(?:pdf|docx|xlsx|xls))(?:\?[^"\']*)?["\']'
            matches = re.findall(pattern, res.text, re.IGNORECASE)
            seen_names = set()
            for link in matches:
                if len(downloaded) >= max_files:
                    break
                file_url = urllib.parse.urljoin(url, link)
                raw_name = os.path.basename(urllib.parse.urlparse(file_url).path)
                clean_name = re.sub(r'[^a-zA-Z0-9_.\-]', '_', raw_name)
                if not clean_name or clean_name.lower() in seen_names:
                    continue
                seen_names.add(clean_name.lower())

                dest_file = os.path.join(dest_dir, clean_name)
                try:
                    f_res = requests.get(file_url, headers=headers, timeout=30, verify=False, stream=True)
                    if f_res.status_code == 200:
                        with open(dest_file, "wb") as f:
                            for chunk in f_res.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded.append(clean_name)
                        print(f"[Radar Auto-Download] Pliego descargado automáticamente: {clean_name}")
                except Exception as dl_err:
                    print(f"[Radar Auto-Download] Error al descargar {file_url}: {dl_err}")
    except Exception as e:
        print(f"[Radar Auto-Download] Error inspeccionando {url}: {e}")

    return downloaded


@app.post("/api/radar/opportunities/{opp_id}/approve")
def approve_opportunity(opp_id: int, background_tasks: BackgroundTasks):
    opps = get_all_opportunities()
    opp = next((o for o in opps if o["id"] == opp_id), None)
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")

    tender_name = f"{opp.get('portal_name', 'Web')}: {opp.get('title', 'Licitación Web')[:80]}"
    tender_id = create_tender(tender_name)

    tender_dir = os.path.join(TENDERS_DIR, str(tender_id), "docs")
    os.makedirs(tender_dir, exist_ok=True)
    brief_path = os.path.join(tender_dir, "Aviso_Licitacion_Web.txt")
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write(f"PUBLICACIÓN OFICIAL DE LICITACIÓN\n")
        f.write(f"Entidad: {opp.get('portal_name')}\n")
        f.write(f"Título: {opp.get('title')}\n")
        f.write(f"URL Oficial: {opp.get('url')}\n")
        f.write(f"Detalle / Snippet: {opp.get('snippet')}\n")
        f.write(f"Palabras clave coincidentes: {opp.get('matched_keywords')}\n")

    # Intentar descargar pliegos públicos automáticamente si existen en la página
    auto_downloaded = try_download_portal_attachments(opp.get('url', ''), tender_dir)

    update_opportunity_status(opp_id, "APROBADA", tender_id=tender_id)
    background_tasks.add_task(process_tender, tender_id)

    if auto_downloaded:
        msg = f"¡Oportunidad aprobada! Se descargaron automáticamente {len(auto_downloaded)} pliego(s). El análisis de IA ha iniciado en segundo plano."
    else:
        msg = f"Licitación #{tender_id} creada con la información oficial. Como el portal no posee pliegos públicos directos (requiere usuario de proveedor o no están adjuntos), puedes abrir la licitación para adjuntar los pliegos y anexos descargados."

    return {
        "status": "success",
        "tender_id": tender_id,
        "auto_downloaded_count": len(auto_downloaded),
        "message": msg
    }

@app.post("/api/radar/opportunities/{opp_id}/reject")
def reject_opportunity(opp_id: int):
    update_opportunity_status(opp_id, "DESCARTADA")
    return {"status": "success", "message": "Oportunidad descartada permanentemente del radar."}

@app.delete("/api/radar/opportunities/{opp_id}")
def delete_opportunity(opp_id: int):
    delete_radar_opportunity(opp_id)
    return {"status": "success", "message": "Oportunidad eliminada permanentemente del radar."}

@app.post("/api/radar/scan")
def trigger_radar_scan(background_tasks: BackgroundTasks):
    from src.core.web_scanner import WebTenderScanner
    def run_scan():
        try:
            scanner = WebTenderScanner()
            scanner.scan_all_portals()
        except Exception as e:
            print(f"[Radar Error] Error durante escaneo: {e}")

    background_tasks.add_task(run_scan)
    return {"status": "success", "message": "Escaneo de portales web iniciado en segundo plano."}

@app.get("/api/radar/weekly-digest-status")
def get_weekly_digest_status():
    from src.core.radar_scheduler import check_and_send_friday_digest
    return check_and_send_friday_digest(force=False)

@app.post("/api/radar/send-weekly-digest")
def send_weekly_digest_now():
    from src.core.radar_scheduler import check_and_send_friday_digest
    res = check_and_send_friday_digest(force=True)
    return res

@app.get("/api/radar/portals")
def list_portals():
    return get_monitored_portals()

class PortalCreateRequest(BaseModel):
    name: str
    url: str
    frequency: str = "Diaria"

@app.post("/api/radar/portals")
def create_portal(req: PortalCreateRequest):
    if not req.name.strip() or not req.url.strip().startswith("http"):
        raise HTTPException(status_code=400, detail="Ingresa un nombre y una URL válida que comience con http:// o https://")
    portal_id = add_monitored_portal(req.name, req.url, req.frequency)
    return {"status": "success", "id": portal_id}

@app.put("/api/radar/portals/{portal_id}/toggle")
def toggle_portal(portal_id: int):
    portals = get_monitored_portals()
    portal = next((p for p in portals if p["id"] == portal_id), None)
    if not portal:
        raise HTTPException(status_code=404, detail="Portal no encontrado")
    new_active = 0 if portal.get("active", 1) else 1
    toggle_monitored_portal(portal_id, new_active)
    return {"status": "success", "active": new_active}

@app.delete("/api/radar/portals/{portal_id}")
def delete_portal(portal_id: int):
    delete_monitored_portal(portal_id)
    return {"status": "success"}

@app.get("/api/radar/keywords")
def list_keywords():
    return get_monitored_keywords()

class KeywordCreateRequest(BaseModel):
    keyword: str

@app.post("/api/radar/keywords")
def create_keyword(req: KeywordCreateRequest):
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="La palabra clave no puede estar vacía.")
    kw_id = add_monitored_keyword(req.keyword)
    return {"status": "success", "id": kw_id}

@app.delete("/api/radar/keywords/{kw_id}")
def delete_keyword(kw_id: int):
    delete_monitored_keyword(kw_id)
    return {"status": "success"}

@app.get("/api/radar/daemon")
def get_daemon_status():
    return {
        "active": is_daemon_active(),
        "settings": get_daemon_settings()
    }

class DaemonUpdateRequest(BaseModel):
    active: Optional[bool] = None
    mail: Optional[bool] = None
    sharepoint: Optional[bool] = None
    pipedrive: Optional[bool] = None
    ai: Optional[bool] = None

@app.post("/api/radar/daemon")
def update_daemon(req: DaemonUpdateRequest):
    if req.active is not None:
        set_daemon_active(req.active)
        if req.active:
            from src.daemon import start_email_daemon
            start_email_daemon()
    if req.mail is not None:
        set_daemon_setting("mail", req.mail)
    if req.sharepoint is not None:
        set_daemon_setting("sharepoint", req.sharepoint)
    if req.pipedrive is not None:
        set_daemon_setting("pipedrive", req.pipedrive)
    if req.ai is not None:
        set_daemon_setting("ai", req.ai)

    return {
        "status": "success",
        "active": is_daemon_active(),
        "settings": get_daemon_settings()
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "database": "postgres",
        "version": "3.0.0"
    }
