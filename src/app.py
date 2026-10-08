import streamlit as st
import os
import sys
import subprocess
import shutil
import time
import pandas as pd
import glob
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def format_datetime_arg(dt_str):
    if not dt_str: return ""
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime, timezone
        if len(dt_str) > 19:
            dt_str = dt_str[:19] # Truncate microseconds if any
        utc_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        arg_tz = ZoneInfo('America/Argentina/Buenos_Aires')
        arg_dt = utc_dt.astimezone(arg_tz)
        return arg_dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_str

st.set_page_config(
    page_title="IMA Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.db.models import (
    init_db, create_tender, get_all_tenders, get_tender, update_tender_parsed_data, 
    add_message, get_messages, delete_tender,
    get_monitored_portals, get_monitored_keywords, get_pending_opportunities, 
    get_all_opportunities, update_opportunity_status,
    is_daemon_active, set_daemon_active
)
from src.ui.view_configuracion import render_view_configuracion

from src.ui.theme import apply_theme, render_metric_card, get_progress_bar_html, get_status_badge, render_version_table_header, render_info_list_item
import streamlit_antd_components as sac
from src.ui.components import save_uploaded_files
from src.ui.tabs.tab_documentos import render_tab_documentos
from src.ui.tabs.tab_ot import render_tab_ot
from src.ui.tabs.tab_rfi import render_tab_rfi
from src.ui.tabs.tab_eco import render_tab_eco


# Inicializar Base de Datos
print("=== [IMA-AGENT DEBUG] Inicializando Base de Datos ===", flush=True)
init_db()
print("=== [IMA-AGENT DEBUG] Base de Datos Inicializada ===", flush=True)

from src.ui.login import render_login_page

# --- Autenticación ---

def navigate_to(view_name):
    st.session_state['current_view'] = view_name
    st.session_state['show_radar_modal'] = False
    st.rerun()

def view_login():
    render_login_page()

def launch_background_worker(tender_id):
    import threading
    
    def worker_wrapper(t_id):
        from src.background_worker import process_tender
        process_tender(t_id)
    
    print(f"=== [IMA-AGENT DEBUG] Lanzando thread de background_worker para tender_id {tender_id} ===", flush=True)
    try:
        thread = threading.Thread(target=worker_wrapper, args=(tender_id,))
        thread.daemon = False  # Keep alive until done
        
        # Opcional: inyectar el contexto de Streamlit por si el worker usa algo de st.
        try:
            from streamlit.runtime.scriptrunner import add_script_run_ctx
            add_script_run_ctx(thread)
        except Exception:
            pass
            
        thread.start()
        print("=== [IMA-AGENT DEBUG] Thread lanzado con éxito ===", flush=True)
    except Exception as e:
        print(f"=== [IMA-AGENT DEBUG] Fallo al lanzar el thread: {e} ===", flush=True)

@st.dialog("🚨 Oportunidad Detectada por el Radar Web", width="large")
def opportunity_confirmation_modal(opp):
    st.markdown(f"<div style='font-size: 0.9rem; color: #2563EB; font-weight: 700; text-transform: uppercase;'>🏢 {opp.get('portal_name', 'Portal Oficial')}</div>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 4px; color: #0F172A;'>{opp.get('title')}</h3>", unsafe_allow_html=True)
    
    if opp.get('snippet'):
        st.markdown(f"<p style='color: #475569; font-size: 0.95rem; background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0;'>{opp.get('snippet')}</p>", unsafe_allow_html=True)
        
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**🎯 Palabras Clave Coincidentes:** `{opp.get('matched_keywords', 'N/A')}`")
    with c2:
        if opp.get('url'):
            st.markdown(f"**🌐 Enlace Oficial:** [{opp.get('portal_name')}]({opp.get('url')})")
            
    st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-weight: 600; color: #1E293B;'>¿Deseas confirmar esta licitación y comenzar el análisis integral inteligente (<strong>'El Show'</strong>)?</p>",
        unsafe_allow_html=True
    )
    
    col_yes, col_no, col_cfg = st.columns([2.2, 1.2, 1.4])
    with col_yes:
        if st.button("🚀 ¡Sí, Iniciar Show! (Analizar)", type="primary", use_container_width=True, key=f"modal_accept_{opp['id']}"):
            tender_name = f"{opp.get('portal_name', 'Web')}: {opp.get('title', 'Licitación Web')[:80]}"
            tender_id = create_tender(tender_name)
            
            tender_dir = os.path.join("data", "tenders", str(tender_id), "docs")
            os.makedirs(tender_dir, exist_ok=True)
            brief_path = os.path.join(tender_dir, "Aviso_Licitacion_Web.txt")
            with open(brief_path, "w", encoding="utf-8") as f:
                f.write(f"PUBLICACIÓN OFICIAL DE LICITACIÓN\n")
                f.write(f"Entidad: {opp.get('portal_name')}\n")
                f.write(f"Título: {opp.get('title')}\n")
                f.write(f"URL Oficial: {opp.get('url')}\n")
                f.write(f"Detalle / Snippet: {opp.get('snippet')}\n")
                f.write(f"Palabras clave coincidentes: {opp.get('matched_keywords')}\n")

            update_opportunity_status(opp['id'], "APROBADA", tender_id=tender_id)
            launch_background_worker(tender_id)
            
            st.session_state['current_tender_id'] = tender_id
            st.session_state['current_view'] = 'detalle'
            st.session_state['show_radar_modal'] = False
            st.rerun()
            
    with col_no:
        if st.button("❌ Descartar", use_container_width=True, key=f"modal_reject_{opp['id']}"):
            update_opportunity_status(opp['id'], "DESCARTADA")
            st.session_state['show_radar_modal'] = False
            st.rerun()
            
    with col_cfg:
        if st.button("⚙️ Ver Todas", use_container_width=True, key=f"modal_goto_cfg_{opp['id']}"):
            st.session_state['current_view'] = 'configuracion'
            st.session_state['show_radar_modal'] = False
            st.rerun()





def view_dashboard():
    
    st.markdown("<h1>Dashboard de Licitaciones</h1>", unsafe_allow_html=True)
    st.markdown("<p>Monitoreo automático de nuevas oportunidades y estado de tus licitaciones.</p>", unsafe_allow_html=True)
    
    tenders = get_all_tenders()
    total = len(tenders)
    procesando = sum(1 for t in tenders if t['status'] == 'PROCESANDO')
    completadas = sum(1 for t in tenders if t['status'] == 'COMPLETADO')
    
    
    from datetime import datetime, timedelta
    now = datetime.now()
    semana_pasada = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    
    nuevas_esta_semana = sum(1 for t in tenders if str(t.get('created_at', '')) >= semana_pasada)
    
    # 3 Top Cards
    c1, c2, c3 = st.columns(3)
    with c1:
        subtitle_tenders = f"+{nuevas_esta_semana} esta semana" if nuevas_esta_semana > 0 else "Sin nuevas esta semana"
        render_metric_card("Licitaciones Totales", str(total), subtitle_tenders, "📋")
    with c2:
        pct_proc = int((procesando/total)*100) if total > 0 else 0
        render_metric_card("En Proceso", str(procesando), f"{pct_proc}% del total", "🔄")
    with c3:
        pct_comp = int((completadas/total)*100) if total > 0 else 0
        render_metric_card("Completadas", str(completadas), f"{pct_comp}% del total", "✅")
    
    # --- RADAR DE LICITACIONES PENDIENTES ---
    pending_opps = get_pending_opportunities()
    if pending_opps:
        first_opp = pending_opps[0]
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #1E293B, #0F172A); border-left: 5px solid #2563EB; border-radius: 8px; padding: 14px 18px; margin-top: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="color: #60A5FA; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; gap: 8px;">
                        📡 RADAR DE LICITACIONES: {len(pending_opps)} OPORTUNIDAD(ES) DETECTADA(S) EN LA WEB
                    </div>
                    <div style="color: #E2E8F0; font-size: 0.9rem; margin-top: 4px;">
                        Nueva licitación encontrada en <strong>{first_opp.get('portal_name')}</strong>: <em>"{first_opp.get('title')[:80]}..."</em>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c_rad_info, c_rad_btn1, c_rad_btn2 = st.columns([3, 1.5, 1.2])
        with c_rad_info:
            st.caption(f"Coincidencia con: '{first_opp.get('matched_keywords')}'. Puedes aprobarla para empezar el análisis o revisarla.")
        with c_rad_btn1:
            if st.button("🚨 Revisar Oportunidad (Pop-up)", type="primary", use_container_width=True, key="btn_trigger_radar_modal"):
                st.session_state['show_radar_modal'] = True
        with c_rad_btn2:
            if st.button("⚙️ Configuración", use_container_width=True, key="btn_dash_cfg_radar"):
                navigate_to('configuracion')

        if st.session_state.get('show_radar_modal', False):
            opportunity_confirmation_modal(first_opp)

    # Control Interactivo del Daemon de Automatización (Toggle ON/OFF)
    # El control del daemon fue movido a la sección de Configuración
    
    col_t, col_b = st.columns([7, 2])
    with col_t:
        st.markdown("### Estado de tus licitaciones\n<p style='margin-top:-10px; font-size: 14px;'>Revisa el estado actual o crea una nueva manualmente.</p>", unsafe_allow_html=True)
    with col_b:
        st.write("") # Espaciador
        if st.button("+ Nueva Licitación", type="primary", use_container_width=True):
            navigate_to('nueva_licitacion')

    # Data Table Header
    h1, h2, h3, h4, h5 = st.columns([1.3, 1.3, 1.3, 2.1, 2.0], gap="small")
    header_style = "font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; text-align: center;"
    h1.markdown(f"<div style='{header_style}; text-align: left;'>Cliente</div>", unsafe_allow_html=True)
    h2.markdown(f"<div style='{header_style}'>Estado</div>", unsafe_allow_html=True)
    h3.markdown(f"<div style='{header_style}'>Última Actualización</div>", unsafe_allow_html=True)
    h4.markdown(f"<div style='{header_style}'>Progreso</div>", unsafe_allow_html=True)
    h5.markdown(f"<div style='{header_style}'>Acciones</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 10px 0; border-color: #E2E8F0; border-width: 2px;'/>", unsafe_allow_html=True)
    
    if not tenders:
        st.write("No hay licitaciones registradas.")
        return
        
    for tender in tenders:
        col1, col2, col3, col4, col5 = st.columns([1.3, 1.3, 1.3, 2.1, 2.0], gap="small")
        with col1:
            st.markdown(f"<div style='font-weight: 600; color: #0F172A; display: flex; align-items: center; gap: 10px;'><div style='width: 32px; height: 32px; border-radius: 50%; border: 1px solid #E2E8F0; display:flex; align-items:center; justify-content:center;'>🏢</div> {tender['name']}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='text-align: center;'>{get_status_badge(tender['status'])}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='text-align: center; font-size: 13px; font-weight: 600; color: #0F172A;'>{format_datetime_arg(tender['created_at'])}</div>", unsafe_allow_html=True)
        with col4:
            pct = tender.get('progress') if tender.get('progress') is not None else (100 if tender['status'] == 'COMPLETADO' else 45 if tender['status'] == 'PROCESANDO' else 0)
            st.markdown(f"<div style='display: flex; justify-content: center; margin-top: 8px;'>{get_progress_bar_html(pct, tender['status'])}</div>", unsafe_allow_html=True)
        with col5:
            # Sub-columnas para que los botones queden lado a lado sin CSS pesado
            btn_col1, btn_col2 = st.columns(2, gap="small")
            with btn_col1:
                is_error = tender['status'] == 'ERROR'
                is_processing = tender['status'] == 'PROCESANDO'
                btn_disabled = is_error or is_processing
                
                help_text_abrir = "Abrir detalle"
                if is_error: help_text_abrir = "Procesamiento fallido"
                elif is_processing: help_text_abrir = "Análisis en progreso"
                
                if st.button("Abrir 📂", key=f"op_{tender['id']}", use_container_width=True, help=help_text_abrir, disabled=btn_disabled):
                    st.session_state['current_tender_id'] = tender['id']
                    navigate_to('detalle')
            with btn_col2:
                help_text_borrar = "Eliminar licitación"
                if is_processing: help_text_borrar = "No se puede borrar mientras procesa"
                
                if st.button("Borrar 🗑️", key=f"del_{tender['id']}", use_container_width=True, help=help_text_borrar, disabled=is_processing):
                    delete_tender(tender['id'])
                    shutil.rmtree(os.path.join("data", "tenders", str(tender['id'])), ignore_errors=True)
                    st.rerun()
        st.markdown("<hr style='margin: 0; border-color: #F1F5F9;'/>", unsafe_allow_html=True)
        
    if procesando > 0:
        with st.container():
            st.markdown("<div style='display:none;'>", unsafe_allow_html=True)
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=3000, key="dashboard_autorefresh")
            st.markdown("</div>", unsafe_allow_html=True)

def view_new_tender():
    st.title("Nueva Licitación 📂")
    st.markdown("Sube los pliegos y anexos. El sistema los procesará en segundo plano.")
    tender_name = st.text_input("Nombre de la Licitación / Proyecto", placeholder="Ej: Licitación YPF Mantenimiento")
    uploaded_files = st.file_uploader("Arrastra los pliegos aquí", type=["pdf", "docx", "xlsx", "xls"], accept_multiple_files=True)
    if st.button("Procesar Archivos en Segundo Plano", type="primary", use_container_width=True):
        print(f"=== [IMA-AGENT DEBUG] Botón presionado para crear licitación: {tender_name} ===", flush=True)
        if not tender_name or not uploaded_files:
            st.warning("Faltan datos.")
            return
        with st.spinner("Creando entorno seguro..."):
            print(f"=== [IMA-AGENT DEBUG] Creando tender en DB ===", flush=True)
            tender_id = create_tender(tender_name)
            print(f"=== [IMA-AGENT DEBUG] Guardando archivos subidos para tender {tender_id} ===", flush=True)
            try:
                save_uploaded_files(uploaded_files, tender_id)
                print(f"=== [IMA-AGENT DEBUG] Archivos guardados correctamente ===", flush=True)
            except Exception as e:
                print(f"=== [IMA-AGENT DEBUG] Error al guardar archivos: {e} ===", flush=True)
                
            print(f"=== [IMA-AGENT DEBUG] Lanzando worker ===", flush=True)
            launch_background_worker(tender_id)
        st.success("¡Archivos enviados a procesamiento!")
        navigate_to('dashboard')

@st.dialog("Gestor de Consultas e Incongruencias", width="large")
def rfi_modal(tender_id, parsed_data):
    st.markdown("Revisa y edita el detalle completo de las consultas detectadas en los pliegos.")
    
    inconsistencias = parsed_data.get("inconsistencias", [])
    consultas = parsed_data.get("consultas_generales", [])
    
    with st.form("rfi_edit_form"):
        st.markdown("### ⚠️ Inconsistencias (Alertas)")
        new_inconsistencias = []
        if inconsistencias:
            for i, inc in enumerate(inconsistencias):
                col1, col2 = st.columns([1, 2])
                docs = inc.get("documentos_conflicto", "")
                docs_str = ", ".join(docs) if isinstance(docs, list) else docs
                
                with col1:
                    tipo = st.text_input("Tipo de Alerta", value=inc.get("tipo", ""), key=f"inc_tipo_{i}")
                    new_docs = st.text_input("Documentos Relacionados", value=docs_str, key=f"inc_docs_{i}")
                with col2:
                    desc = st.text_area("Descripción", value=inc.get("descripcion", ""), key=f"inc_desc_{i}", height=110)
                
                new_inconsistencias.append({
                    "tipo": tipo,
                    "documentos_conflicto": [d.strip() for d in new_docs.split(',')] if new_docs else [],
                    "descripcion": desc
                })
                st.markdown("<hr style='margin: 5px 0; border-color: #F1F5F9;'/>", unsafe_allow_html=True)
        else:
            st.info("Ninguna detectada.")
            
        st.markdown("### ❓ Consultas Generales")
        new_consultas = []
        if consultas:
            for i, c in enumerate(consultas):
                col1, col2 = st.columns([1, 2])
                with col1:
                    cat = st.text_input("Categoría", value=c.get("categoria", ""), key=f"con_cat_{i}")
                    origen = st.text_input("Archivo Origen", value=c.get("archivo_origen", ""), key=f"con_ori_{i}")
                with col2:
                    desc = st.text_area("Descripción de la Consulta", value=c.get("consulta", ""), key=f"con_desc_{i}", height=110)
                
                new_consultas.append({
                    "categoria": cat,
                    "archivo_origen": origen,
                    "consulta": desc
                })
                st.markdown("<hr style='margin: 5px 0; border-color: #F1F5F9;'/>", unsafe_allow_html=True)
        else:
            st.info("Ninguna consulta extra.")
            
        submit = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)
        if submit:
            parsed_data["inconsistencias"] = new_inconsistencias
            parsed_data["consultas_generales"] = new_consultas
            update_tender_parsed_data(tender_id, parsed_data)
            st.success("¡Cambios guardados correctamente!")
            time.sleep(1)
            st.rerun()
            
    if st.button("Cerrar y Volver", use_container_width=True):
        st.rerun()

def view_tender_detail():
    tender_id = st.session_state.get('current_tender_id')
    tender = get_tender(tender_id)
    if not tender: return st.error("No existe.")
    
    # Header with toggle button
    h_col1, h_col2 = st.columns([6, 1])
    with h_col1:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 15px; margin-top: 10px;">
                <div style="background: #2563EB; width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; color: white;">📁</div>
                <div>
                    <h1 style="margin: 0; font-size: 28px; line-height: 1;">{tender['name']}</h1>
                    <div style="font-size: 12px; color: #64748B; margin-top: 4px;">Creada: {format_datetime_arg(tender['created_at'])} | Última actualización: Reciente</div>
                </div>
            </div>
            <br/>
        """, unsafe_allow_html=True)
    with h_col2:
        st.write("")
                
    if tender['status'] == 'PROCESANDO':
        def render_processing_view():
            current_tender = get_tender(tender_id)
            if current_tender['status'] != 'PROCESANDO':
                st.rerun()
            progress_val = current_tender.get('progress', 0)
            progress_msg = current_tender.get('progress_msg', 'Procesando en segundo plano...')
            st.info(f"⏳ **{progress_msg}** (La pantalla se actualizará automáticamente)")
            st.progress(progress_val)
        render_processing_view()
        
        with st.container():
            st.markdown("<div style='display:none;'>", unsafe_allow_html=True)
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=3000, key=f"tender_refresh_{tender_id}")
            st.markdown("</div>", unsafe_allow_html=True)
            
        return
    outputs_dir = os.path.join("data", "tenders", str(tender_id), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    parsed_data = tender.get('parsed_data') or {}
    
    cliente = parsed_data.get("metadata", {}).get("cliente", "Cliente")
    safe_cliente = re.sub(r'[^\w\s-]', '', cliente).strip().replace(' ', '_')[:20]
    
    # Detección de tareas de IA en segundo plano para esta licitación
    from src.core.chat_worker import is_chat_job_running
    if is_chat_job_running(tender_id):
        def render_bg_job_alert():
            if not is_chat_job_running(tender_id):
                st.rerun()
            st.markdown(
            """
            <div style="background-color: #EFF6FF; border: 1.5px solid #93C5FD; border-left: 5px solid #2563EB; border-radius: 10px; padding: 12px 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(37,99,235,0.06);">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.4rem;">🤖</span>
                    <div>
                        <div style="font-weight: 700; color: #1E40AF; font-size: 0.95rem;">Asistente IA generando nueva versión en segundo plano...</div>
                        <div style="color: #2563EB; font-size: 0.82rem; margin-top: 2px;">El documento se está ensamblando con las instrucciones del pop-up. Esta vista se actualizará automáticamente apenas esté listo.</div>
                    </div>
                </div>
                <span style="background-color: #DBEAFE; color: #1D4ED8; font-size: 0.72rem; font-weight: 800; padding: 4px 12px; border-radius: 20px; letter-spacing: 0.5px;">EN PROCESO</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        render_bg_job_alert()

    # Column configuration
    cols_config = [1.2, 2.4]
        
    tab_docs, tab_rfi, tab_ot, tab_eco = st.tabs(["📁 Documentos", "❓ Consultas (RFI)", "📄 Oferta Técnica", "📊 Oferta Económica"])
    
    with tab_docs:
        render_tab_documentos(tender_id, cols_config)
        
    with tab_rfi:
        render_tab_rfi(tender_id, parsed_data, outputs_dir, safe_cliente, cols_config)
        
    with tab_ot:
        render_tab_ot(tender_id, parsed_data, outputs_dir, safe_cliente, cols_config)
        
    with tab_eco:
        render_tab_eco(tender_id, parsed_data, outputs_dir, safe_cliente, cols_config)
@st.cache_resource
def start_daemon():
    print("=== [IMA-AGENT DEBUG] Iniciando Daemon (start_daemon) ===", flush=True)
    daemon_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon.py")
    try:
        daemon_log = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "daemon.log")
        f_daemon = open(daemon_log, "w")
        subprocess.Popen(
            [sys.executable, daemon_script],
            stdout=f_daemon,
            stderr=subprocess.STDOUT,
            close_fds=True
        )
        print("=== [IMA-AGENT DEBUG] Daemon lanzado correctamente ===", flush=True)
    except Exception as e:
        print(f"=== [IMA-AGENT DEBUG] Error al lanzar daemon: {e} ===", flush=True)
    return True

def main():
    print("=== [IMA-AGENT DEBUG] Iniciando aplicación (main) ===", flush=True)
    # Iniciar el agente automático en segundo plano
    start_daemon()
    
    print(f"=== [IMA-AGENT DEBUG] st.session_state actual: {st.session_state} ===", flush=True)
    if "token" in st.query_params and not st.session_state.get('authenticated', False):
        try:
            import base64
            user = base64.b64decode(st.query_params["token"]).decode("utf-8")
            st.session_state['authenticated'] = True
            st.session_state['current_user'] = user
        except:
            pass

    apply_theme()

    if not st.session_state.get('authenticated', False):
        return view_login()

    if 'current_view' not in st.session_state:
        st.session_state['current_view'] = 'dashboard'

    with st.sidebar:
        st.markdown("<h1 style='color: white; font-size: 2.2rem; font-weight: 900;'><span style='color: #A3E635;'>i</span>ma</h1>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 10px; color: #94A3B8; margin-top: -10px; margin-bottom: 20px;'>SI | Argentina HOLDAS Latam</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;'>🤖 IMA Agent</div>", unsafe_allow_html=True)
        
        if st.button("🏠 Dashboard", use_container_width=True): 
            navigate_to('dashboard')
        if st.button("➕ Nueva Licitación", use_container_width=True): 
            navigate_to('nueva_licitacion')
            
        if st.button("⚙️ Configuración", use_container_width=True):
            navigate_to('configuracion')
            
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state['authenticated'] = False
            st.session_state.pop('current_user', None)
            st.query_params.clear()
            navigate_to('dashboard')
        
        st.markdown("<br><br><br><div style='font-size: 11px; color: #94A3B8;'>IMA Servicios Industriales<br>Plataforma Automática V3.0</div>", unsafe_allow_html=True)


    print(f"=== [IMA-AGENT DEBUG] Renderizando vista: {st.session_state.get('current_view')} ===", flush=True)

    if st.session_state['current_view'] == 'dashboard': view_dashboard()
    elif st.session_state['current_view'] == 'nueva_licitacion': view_new_tender()
    elif st.session_state['current_view'] == 'detalle': view_tender_detail()
    elif st.session_state['current_view'] == 'configuracion': render_view_configuracion(launch_background_worker)
    print("=== [IMA-AGENT DEBUG] Fin de renderizado de la vista ===", flush=True)

if __name__ == "__main__":
    main()
