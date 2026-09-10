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

from src.db.models import init_db, create_tender, get_all_tenders, get_tender, update_tender_parsed_data, add_message, get_messages, delete_tender
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

# Inicializar Base de Datos
init_db()

# --- Autenticación ---
def view_login():
    st.title("🔒 Acceso Restringido")
    st.markdown("Plataforma de IA para Gestión de Licitaciones - IMA Servicios Industriales")
    with st.form("login_form"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar", type="primary")
        if submit:
            if user == "admin" and password == "Ima2026!":
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")

def launch_background_worker(tender_id):
    worker_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background_worker.py")
    subprocess.Popen([sys.executable, worker_script, str(tender_id)])

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
    
    st.write("")
    st.info("🔔 **Notificación:** El sistema está monitoreando en segundo plano los ingresos de nuevas licitaciones.")
    st.write("")
    
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
        
        if st.button("🏠 Dashboard", use_container_width=True): st.session_state['current_view'] = 'dashboard'
        if st.button("➕ Nueva Licitación", use_container_width=True): st.session_state['current_view'] = 'nueva_licitacion'
        
        st.markdown("<br><br><br><div style='font-size: 11px; color: #94A3B8;'>IMA Servicios Industriales<br>Plataforma Automática V3.0</div>", unsafe_allow_html=True)

    if st.session_state['current_view'] == 'dashboard': view_dashboard()
    elif st.session_state['current_view'] == 'nueva_licitacion': view_new_tender()
    elif st.session_state['current_view'] == 'detalle': view_tender_detail()

if __name__ == "__main__":
    main()
