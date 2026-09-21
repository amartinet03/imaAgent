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

from src.db.models import (
    init_db, create_tender, get_all_tenders, get_tender, update_tender_parsed_data, 
    add_message, get_messages, delete_tender,
    get_monitored_portals, get_monitored_keywords, get_pending_opportunities, 
    get_all_opportunities, update_opportunity_status,
    is_daemon_active, set_daemon_active
)
from src.ui.view_configuracion import render_view_configuracion
from src.outputs.excel_generator import ExcelGenerator
from src.outputs.word_generator import WordGenerator
from src.outputs.query_generator import QueryGenerator
from src.core.chat_modifier import modify_json_with_chat
from src.ui.theme import apply_theme, render_metric_card, get_progress_bar_html, get_status_badge, render_version_table_header, render_info_list_item
import streamlit_antd_components as sac
from streamlit_autorefresh import st_autorefresh
from src.ui.components import save_uploaded_files
from src.ui.tabs.tab_documentos import render_tab_documentos
from src.ui.tabs.tab_ot import render_tab_ot
from src.ui.tabs.tab_rfi import render_tab_rfi
from src.ui.tabs.tab_eco import render_tab_eco
from src.core.chat_worker import is_chat_job_running

# Inicializar Base de Datos
init_db()

from src.ui.login import render_login_page

# --- Autenticación ---
def view_login():
    render_login_page()

def launch_background_worker(tender_id):
    worker_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background_worker.py")
    subprocess.Popen([sys.executable, worker_script, str(tender_id)])

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


def render_daemon_control():
    """
    Componente interactivo para activar o desactivar el Daemon de Automatización.
    Por defecto está apagado. Cuando se activa, el servicio en segundo plano:
    1. Busca licitaciones en la bandeja de entrada del correo (Microsoft 365).
    2. Crea la estructura completa de carpetas en SharePoint.
    3. Registra el negocio en Pipedrive CRM.
    4. Descarga pliegos y lanza el análisis técnico con Inteligencia Artificial.
    """
    daemon_active = is_daemon_active()

    if daemon_active:
        card_bg = "#F0FDF4"
        card_border = "#86EFAC"
        badge_bg = "#DCFCE7"
        badge_color = "#15803D"
        icon_status = "🟢"
        badge_label = "AUTOMATIZACIÓN ACTIVA (ON)"
        status_description = (
            "<strong>⚡ El Daemon de Automatización está corriendo en segundo plano:</strong> "
            "Revisa continuamente el correo electrónico (Microsoft 365) para detectar pliegos y llamados a licitación. "
            "Al encontrar una oportunidad, crea de inmediato la estructura en <strong>SharePoint</strong>, "
            "genera el negocio en <strong>Pipedrive CRM</strong> y dispara el análisis de requerimientos con <strong>Inteligencia Artificial</strong>."
        )
    else:
        card_bg = "#F8FAFC"
        card_border = "#CBD5E1"
        badge_bg = "#F1F5F9"
        badge_color = "#64748B"
        icon_status = "⚪"
        badge_label = "AUTOMATIZACIÓN EN PAUSA (OFF)"
        status_description = (
            "<strong>⏸️ Daemon en modo seguro (Apagado por defecto):</strong> "
            "No se revisarán correos entrantes ni se crearán carpetas en <strong>SharePoint</strong> ni negocios en <strong>Pipedrive</strong> "
            "automáticamente. Activá el interruptor para iniciar el monitoreo y sincronización automática."
        )

    st.markdown(
        f"""
        <div style="background-color: {card_bg}; border: 1.5px solid {card_border}; border-radius: 12px; padding: 16px 20px; margin: 15px 0 10px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.2rem;">{icon_status}</span>
                    <span style="font-weight: 700; color: #0F172A; font-size: 1rem;">Daemon de Automatización de Licitaciones</span>
                </div>
                <span style="background-color: {badge_bg}; color: {badge_color}; font-size: 0.72rem; font-weight: 800; padding: 4px 12px; border-radius: 20px; letter-spacing: 0.5px; border: 1px solid {card_border};">
                    {badge_label}
                </span>
            </div>
            <div style="color: #475569; font-size: 0.86rem; line-height: 1.55; margin-bottom: 12px;">
                {status_description}
            </div>
            <div style="display: flex; gap: 16px; align-items: center; font-size: 0.8rem; color: #64748B; padding-top: 8px; border-top: 1px dashed {card_border};">
                <span>📩 Búsqueda en Mail: <strong style="color: {'#16A34A' if daemon_active else '#64748B'};">{'Activa' if daemon_active else 'En pausa'}</strong></span>
                <span>📁 Creación SharePoint: <strong style="color: {'#16A34A' if daemon_active else '#64748B'};">{'Activa' if daemon_active else 'En espera'}</strong></span>
                <span>🤝 Oportunidades Pipedrive: <strong style="color: {'#16A34A' if daemon_active else '#64748B'};">{'Automático' if daemon_active else 'Manual'}</strong></span>
                <span>🤖 Análisis Técnico IA: <strong style="color: {'#16A34A' if daemon_active else '#64748B'};">{'En cola' if daemon_active else 'Standby'}</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    c_note, c_switch = st.columns([3.2, 1.8])
    with c_note:
        st.markdown(
            "<p style='color: #64748B; font-size: 0.8rem; margin: 4px 0 0 0;'>"
            "ℹ️ Podés encenderlo o pausarlo en cualquier momento sin afectar las licitaciones existentes."
            "</p>",
            unsafe_allow_html=True
        )
    with c_switch:
        toggle_state = st.toggle(
            "⚡ Activar Daemon de Automatización",
            value=daemon_active,
            key="dash_toggle_daemon_active",
            help="Habilitar para buscar licitaciones en el correo y sincronizar con SharePoint y Pipedrive."
        )
        if toggle_state != daemon_active:
            set_daemon_active(toggle_state)
            if toggle_state:
                st.toast("🟢 Daemon activado: monitoreando correos y sincronizando SharePoint y Pipedrive.", icon="🚀")
            else:
                st.toast("⚪ Daemon pausado: automatización en modo seguro.", icon="⏸️")
            st.rerun()


def view_dashboard():
    # Refrescar automáticamente la pantalla cada 15 segundos para ver nuevas licitaciones en tiempo real
    st_autorefresh(interval=15000, key="dashboard_autorefresh")
    
    st.markdown("<h1>Dashboard de Licitaciones</h1>", unsafe_allow_html=True)
    st.markdown("<p>Monitoreo automático de nuevas oportunidades y estado de tus licitaciones.</p>", unsafe_allow_html=True)
    
    tenders = get_all_tenders()
    total = len(tenders)
    procesando = sum(1 for t in tenders if t['status'] == 'PROCESANDO')
    completadas = sum(1 for t in tenders if t['status'] == 'COMPLETADO')
    
    # 4 Top Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Licitaciones Totales", str(total), "+2 esta semana", "📋")
    with c2:
        pct_proc = int((procesando/total)*100) if total > 0 else 0
        render_metric_card("En Proceso", str(procesando), f"{pct_proc}% del total", "🔄")
    with c3:
        pct_comp = int((completadas/total)*100) if total > 0 else 0
        render_metric_card("Completadas", str(completadas), f"{pct_comp}% del total", "✅")
    with c4:
        render_metric_card("IA del Sistema", "Online", "Monitoreo activo", "🤖", is_online=True)
    
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
                st.session_state['current_view'] = 'configuracion'
                st.rerun()

        if st.session_state.get('show_radar_modal', False):
            opportunity_confirmation_modal(first_opp)

    # Control Interactivo del Daemon de Automatización (Toggle ON/OFF)
    render_daemon_control()
    
    col_t, col_b = st.columns([7, 2])
    with col_t:
        st.markdown("### Estado de tus licitaciones\n<p style='margin-top:-10px; font-size: 14px;'>Revisa el estado actual o crea una nueva manualmente.</p>", unsafe_allow_html=True)
    with col_b:
        st.write("") # Espaciador
        if st.button("+ Nueva Licitación", type="primary", use_container_width=True):
            st.session_state['current_view'] = 'nueva_licitacion'
            st.rerun()

    # Data Table Header
    h1, h2, h3, h4, h5 = st.columns([1.8, 1.2, 1.2, 2.0, 1.8], gap="small")
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
        col1, col2, col3, col4, col5 = st.columns([1.8, 1.2, 1.2, 2.0, 1.8], gap="small")
        with col1:
            st.markdown(f"<div style='font-weight: 600; color: #0F172A; display: flex; align-items: center; gap: 10px;'><div style='width: 32px; height: 32px; border-radius: 50%; border: 1px solid #E2E8F0; display:flex; align-items:center; justify-content:center;'>🏢</div> {tender['name']}</div>", unsafe_allow_html=True)
            st.caption(f"Creada: {tender['created_at']}")
        with col2:
            st.markdown(f"<div style='text-align: center;'>{get_status_badge(tender['status'])}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='text-align: center; font-size: 13px; font-weight: 600; color: #0F172A;'>{tender['created_at'][:10]}<br><span style='font-size: 11px; color: #64748B; font-weight: 400;'>Hace 1 hora</span></div>", unsafe_allow_html=True)
        with col4:
            pct = 100 if tender['status'] == 'COMPLETADO' else 45 if tender['status'] == 'PROCESANDO' else 0
            st.markdown(f"<div style='display: flex; justify-content: center; margin-top: 8px;'>{get_progress_bar_html(pct, tender['status'])}</div>", unsafe_allow_html=True)
        with col5:
            # Sub-columnas para que los botones queden lado a lado sin CSS pesado
            btn_col1, btn_col2 = st.columns(2, gap="small")
            with btn_col1:
                is_error = tender['status'] == 'ERROR'
                if st.button("Abrir 📂", key=f"op_{tender['id']}", use_container_width=True, help="Abrir detalle" if not is_error else "Procesamiento fallido", disabled=is_error):
                    st.session_state['current_tender_id'] = tender['id']
                    st.session_state['current_view'] = 'detalle'
                    st.rerun()
            with btn_col2:
                if st.button("Borrar 🗑️", key=f"del_{tender['id']}", use_container_width=True, help="Eliminar licitación"):
                    delete_tender(tender['id'])
                    shutil.rmtree(os.path.join("data", "tenders", str(tender['id'])), ignore_errors=True)
                    st.rerun()
        st.markdown("<hr style='margin: 0; border-color: #F1F5F9;'/>", unsafe_allow_html=True)

def view_new_tender():
    st.title("Nueva Licitación 📂")
    st.markdown("Sube los pliegos y anexos. El sistema los procesará en segundo plano.")
    tender_name = st.text_input("Nombre de la Licitación / Proyecto", placeholder="Ej: Licitación YPF Mantenimiento")
    uploaded_files = st.file_uploader("Arrastra los pliegos aquí", type=["pdf", "docx", "xlsx", "xls"], accept_multiple_files=True)
    if st.button("Procesar Archivos en Segundo Plano", type="primary", use_container_width=True):
        if not tender_name or not uploaded_files:
            st.warning("Faltan datos.")
            return
        with st.spinner("Creando entorno seguro..."):
            tender_id = create_tender(tender_name)
            save_uploaded_files(uploaded_files, tender_id)
            launch_background_worker(tender_id)
        st.success("¡Archivos enviados a procesamiento!")
        time.sleep(1)
        st.session_state['current_view'] = 'dashboard'
        st.rerun()

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
    
    # Chat uses dialog now
    
    st.markdown(f"<div style='font-size: 13px; color: #2563EB; font-weight: 500;'>Dashboard > Licitaciones > {tender['name']}</div>", unsafe_allow_html=True)
    
    # Header with toggle button
    h_col1, h_col2 = st.columns([6, 1])
    with h_col1:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 15px; margin-top: 10px;">
                <div style="background: #2563EB; width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; color: white;">📁</div>
                <div>
                    <h1 style="margin: 0; font-size: 28px; line-height: 1;">{tender['name']}</h1>
                    <div style="font-size: 12px; color: #64748B; margin-top: 4px;">Creada: {tender['created_at']} | Última actualización: Reciente</div>
                </div>
            </div>
            <br/>
        """, unsafe_allow_html=True)
    with h_col2:
        st.write("")
                
    if tender['status'] == 'PROCESANDO':
        st.info("Procesando en segundo plano...")
        time.sleep(3)
        st.rerun()
        return
        
    parsed_data = tender.get('parsed_data', {})
    outputs_dir = os.path.join("data", "tenders", str(tender_id), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    cliente = parsed_data.get("metadata", {}).get("cliente", "Cliente")
    safe_cliente = re.sub(r'[^\w\s-]', '', cliente).strip().replace(' ', '_')[:20]
    
    # Detección de tareas de IA en segundo plano para esta licitación
    if is_chat_job_running(tender_id):
        st_autorefresh(interval=3000, key=f"tender_detail_bg_refresh_{tender_id}")
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
    daemon_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon.py")
    # Lanzar el daemon compartiendo la salida con la terminal de Streamlit
    subprocess.Popen([sys.executable, daemon_script])
    return True

def main():
    # Iniciar el agente automático en segundo plano
    start_daemon()
    
    st.set_page_config(page_title="IMA Agent", layout="wide", initial_sidebar_state="expanded")
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
            st.session_state['current_view'] = 'dashboard'
            st.rerun()
        if st.button("➕ Nueva Licitación", use_container_width=True): 
            st.session_state['current_view'] = 'nueva_licitacion'
            st.rerun()
            
        if st.button("⚙️ Configuración", use_container_width=True):
            st.session_state['current_view'] = 'configuracion'
            st.rerun()
            
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state['authenticated'] = False
            st.session_state.pop('current_user', None)
            st.session_state['current_view'] = 'dashboard'
            st.rerun()
        
        st.markdown("<br><br><br><div style='font-size: 11px; color: #94A3B8;'>IMA Servicios Industriales<br>Plataforma Automática V3.0</div>", unsafe_allow_html=True)

    if st.session_state['current_view'] == 'dashboard': view_dashboard()
    elif st.session_state['current_view'] == 'nueva_licitacion': view_new_tender()
    elif st.session_state['current_view'] == 'detalle': view_tender_detail()
    elif st.session_state['current_view'] == 'configuracion': render_view_configuracion(launch_background_worker)

if __name__ == "__main__":
    main()
