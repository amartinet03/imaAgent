import os
import sys
import time
import re
import base64
import threading

# Agregar el root al sys.path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.integrations.crm_client import CRMClient
from src.integrations.ms365_client import MS365Client
from src.db.models import create_tender
from src.background_worker import process_tender

# Cargar variables de entorno
load_dotenv()

def run_periodic_web_scanner():
    """
    Rastreador periódico de portales públicos oficiales en segundo plano.
    Escanea NA-SA, ARSAT y demás portales configurados buscando coincidencias con las palabras clave.
    """
    from src.core.web_scanner import WebTenderScanner
    time.sleep(5)
    while True:
        try:
            print("[Radar Web] Ejecutando escaneo de portales oficiales...")
            scanner = WebTenderScanner()
            res = scanner.scan_all_portals()
            print(f"[Radar Web] Escaneo completado: {res['total_found']} oportunidades ({res['new_detected_count']} nuevas).")
        except Exception as e:
            print(f"[Radar Web] Error en escaneo de portales: {e}")
        # Intervalo de chequeo periódico: cada 4 horas
        time.sleep(4 * 3600)

def run_daemon():
    print("=== Iniciando servicio en segundo plano (Daemon) ===")
    
    # Iniciar hilo en segundo plano para rastreo de páginas web
    web_thread = threading.Thread(target=run_periodic_web_scanner, daemon=True)
    web_thread.start()
    
    ms_client = None
    crm_client = None
    user_email = os.getenv("MS365_MONITOR_EMAIL")
    ignored_messages = set()
    last_active_state = None

    print("📡 Daemon iniciado. Esperando señal de activación desde el panel de control...")
    
    while True:
        try:
            from src.db.models import is_daemon_active
            active = is_daemon_active()

            if active != last_active_state:
                last_active_state = active
                if active:
                    print(f"\n🟢 [DAEMON ACTIVADO] Monitoreando correos ({user_email}) y sincronizando con SharePoint y Pipedrive...")
                else:
                    print(f"\n⚪ [DAEMON EN PAUSA] Automatización detenida. No se leerán correos ni se crearán carpetas/deals.")

            if not active:
                time.sleep(5)
                continue

            if not user_email:
                print("❌ [Daemon] Falta definir MS365_MONITOR_EMAIL en tu archivo .env")
                time.sleep(15)
                continue

            # Conexión perezosa a MS365 y CRM al activarse
            if ms_client is None:
                try:
                    ms_client = MS365Client()
                    ms_client._get_access_token()
                    crm_client = CRMClient()
                    print(f"✅ Conectado a Microsoft 365 exitosamente para: {user_email}")
                except Exception as e:
                    print(f"❌ Error conectando a MS365/CRM: {e}")
                    time.sleep(20)
                    continue

            emails = ms_client.fetch_unread_tender_emails(user_email)
            
            # Filtramos los correos para mostrar solo los nuevos
            new_emails = [e for e in emails if e.get("id") not in ignored_messages]
            
            if new_emails:
                print(f"[{time.strftime('%H:%M:%S')}] Se encontraron {len(new_emails)} correos nuevos por revisar.")
                
            for email in new_emails:
                message_id = email.get("id")
                subject = email.get("subject", "Licitación sin asunto")
                
                # --- Filtro Inteligente Básico ---
                # Más adelante puedes ampliar esta lista con lo que te pase el cliente
                keywords = ["licitacion", "licitación", "pliego", "cotizacion", "cotización", "tender"]
                subject_lower = subject.lower()
                
                is_tender = any(kw in subject_lower for kw in keywords)
                has_attachments = email.get("hasAttachments", False)
                
                if not is_tender:
                    print(f"  [DESCARTADO] El correo '{subject}' no parece ser una licitación. Ignorando...")
                    ignored_messages.add(message_id)
                    continue
                    
                if not has_attachments:
                    print(f"  [DESCARTADO] El correo '{subject}' parece una licitación pero NO tiene archivos adjuntos. Ignorando...")
                    ignored_messages.add(message_id)
                    continue
                # ---------------------------------
                
                from src.db.models import get_all_tenders
                existing_tenders = get_all_tenders()
                
                # Limpiar el asunto para buscar si ya existe
                clean_subject = subject.replace("RE:", "").replace("Re:", "").replace("FW:", "").replace("Fwd:", "").replace("RV:", "").strip()
                
                # Buscar si ya tenemos una licitación con un nombre similar
                matched_tender = None
                for t in existing_tenders:
                    if t['name'].lower() in clean_subject.lower() or clean_subject.lower() in t['name'].lower():
                        matched_tender = t
                        break
                        
                if matched_tender:
                    print(f"\n[ACLARACION/ACTUALIZACION] El correo '{subject}' pertenece a la licitación existente (ID: {matched_tender['id']})")
                    tender_id = matched_tender['id']
                    sp_folder_id = matched_tender.get('parsed_data', {}).get('sp_folder_id')
                else:
                    print(f"\n[NUEVO CORREO DE LICITACION] Procesando: '{subject}'")
                    
                    # Intentar extraer el cliente del correo para usarlo como nombre
                    sender = email.get("sender") or {}
                    email_addr = sender.get("emailAddress") or {}
                    sender_email = email_addr.get("address", "")
                    sender_name = email_addr.get("name", "")
                    body_preview = email.get("bodyPreview") or ""
                    
                    client_name = None
                    try:
                        from src.core.analyzer import get_anthropic_api_key
                        from langchain_anthropic import ChatAnthropic
                        api_key = get_anthropic_api_key()
                        llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", anthropic_api_key=api_key)
                        prompt_text = f"Extrae ÚNICAMENTE el nombre de la empresa cliente (quien emite la licitación) a partir de este correo. Si no estás seguro o no figura, responde exactamente 'Desconocido'. No agregues ninguna otra palabra ni explicación. Asunto: {clean_subject} | De: {sender_name} <{sender_email}> | Cuerpo: {body_preview}"
                        res = llm.invoke(prompt_text)
                        
                        res_text = ""
                        if isinstance(res.content, str):
                            res_text = res.content.strip()
                        elif isinstance(res.content, list):
                            res_text = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in res.content]).strip()
                        else:
                            res_text = str(res.content).strip()
                            
                        if res_text and "desconocido" not in res_text.lower() and len(res_text) < 50:
                            client_name = res_text.replace('"', '').replace("'", "")
                            print(f"  -> Cliente identificado por IA: {client_name}")
                    except Exception as e:
                        print(f"  -> Error extrayendo cliente con IA: {e}")
                        
                    client_name_str = client_name if client_name else "CLIENTE_DESCONOCIDO"
                    
                    # 1. Obtener ID de la planilla y Abreviación del cliente
                    from src.utils.excel_manager import get_next_tender_info
                    print("  -> Obteniendo ID y código de cliente de SharePoint (BD_Oportunidades.xlsx)...")
                    sp_id, sp_client_abbr = get_next_tender_info(ms_client, client_name_str)
                    
                    # 2. Formatear el nombre completo: ID-CLIENTE-TITULO
                    tender_name_formatted = f"{sp_id}-{sp_client_abbr}-{clean_subject}"
                    
                    tender_id = create_tender(tender_name_formatted)
                    print(f"  -> Licitación creada en BD local (ID: {tender_id}) - Nombre: '{tender_name_formatted}'")
                    
                    # 3. Crear estructura en SharePoint
                    print("  -> Creando carpetas en SharePoint...")
                    sp_folder_id = ms_client.setup_tender_sharepoint_folders(user_email, tender_name_formatted)
                    if sp_folder_id:
                        # Guardar el ID de SharePoint en la BD local
                        from src.db.models import update_tender_parsed_data, get_tender
                        t = get_tender(tender_id)
                        pd = t.get('parsed_data', {})
                        pd['sp_folder_id'] = sp_folder_id
                        update_tender_parsed_data(tender_id, pd)
                    
                    # 2. Crear negocio en Pipedrive CRM automáticamente
                    deal_id = crm_client.create_deal(title=tender_name_formatted, value=0.0)
                    if deal_id:
                        print(f"  -> Negocio creado en Pipedrive (ID: {deal_id})")
                
                # 3. Obtener y guardar adjuntos (pliegos, anexos) localmente y en SharePoint
                adjuntos = ms_client.get_email_attachments(user_email, message_id)
                if adjuntos:
                    tender_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'tenders', str(tender_id))
                    docs_dir = os.path.join(tender_dir, 'docs')
                    os.makedirs(docs_dir, exist_ok=True)
                    
                    for adjunto in adjuntos:
                        nombre_archivo = adjunto.get("name")
                        contenido_b64 = adjunto.get("contentBytes")
                        
                        if nombre_archivo and contenido_b64:
                            # Sanitizar nombre de archivo adjunto
                            safe_adjunto_name = os.path.basename(nombre_archivo)
                            safe_adjunto_name = re.sub(r'[^a-zA-Z0-9_.\-\sáéíóúÁÉÍÓÚñÑ()]', '_', safe_adjunto_name).strip()
                            if not safe_adjunto_name:
                                safe_adjunto_name = f"adjunto_{int(time.time())}.bin"
                            # Guardar Local
                            ruta_archivo = os.path.join(docs_dir, safe_adjunto_name)
                            file_bytes = base64.b64decode(contenido_b64)
                            with open(ruta_archivo, "wb") as f:
                                f.write(file_bytes)
                            print(f"  -> Archivo descargado localmente: {safe_adjunto_name}")
                            
                            # Subir a SharePoint a la carpeta "ET" (Especificación Técnica)
                            if sp_folder_id:
                                ms_client.upload_file_to_user_drive(user_email, sp_folder_id, "ET", nombre_archivo, file_bytes)
                                print(f"  -> Archivo subido a SharePoint (/ET): {nombre_archivo}")
                else:
                    print("  -> El correo no tiene adjuntos.")
                
                # 4. Marcar correo como leído
                ms_client.mark_email_as_read(user_email, message_id)
                print("  -> Correo marcado como leído.")
                
                # 5. Lanzar el análisis de IA de forma asíncrona (re-analizará todo incluyendo nuevos archivos)
                print("  -> Iniciando análisis de IA en segundo plano (process_tender)...")
                ia_thread = threading.Thread(target=process_tender, args=(tender_id,))
                ia_thread.start()
                
        except Exception as e:
            print(f"Error en el ciclo del daemon: {e}")
            
        # Esperar 20 segundos antes de volver a revisar la bandeja de entrada,
        # consultando cada 3 segundos si el daemon fue pausado desde el panel
        for _ in range(7):
            from src.db.models import is_daemon_active
            if not is_daemon_active():
                break
            time.sleep(3)

if __name__ == "__main__":
    run_daemon()
