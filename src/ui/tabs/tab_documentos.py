import streamlit as st
import os
import glob
from src.ui.components import save_uploaded_files
from datetime import datetime
from src.db.models import get_connection

@st.dialog("Historial de Interacciones con la IA", width="large")
def render_ia_history(tender_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT role, content, chat_type, created_at FROM messages WHERE tender_id = ? ORDER BY created_at ASC", (tender_id,))
    rows = c.fetchall()
    conn.close()
    
    has_user_interaction = any(row[0] == 'user' for row in rows)
    
    if not rows or not has_user_interaction:
        st.info("No has interactuado con la IA todavía en este proyecto.")
        return
        
    for row in rows:
        role, content, chat_type, created_at = row
        
        try:
            # En la DB la fecha suele estar como 'YYYY-MM-DD HH:MM:SS'
            dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            time_str = dt.strftime("%d/%m/%Y %H:%M")
        except:
            time_str = created_at
            
        if role == "user":
            st.markdown(f"<div style='font-size: 11px; color: #64748B; margin-bottom: 4px;'><b>Tú</b> (Pestaña: {chat_type}) • {time_str}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; color: #0F172A; font-size: 14px; margin-bottom: 12px;'>{content}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size: 11px; color: #64748B; margin-bottom: 4px; margin-top: 12px;'><b>Asistente IA</b> (Pestaña: {chat_type}) • {time_str}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 12px; color: #1E3A8A; font-size: 14px; margin-bottom: 12px;'>{content}</div>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin: 0; border: none; border-bottom: 1px solid #F1F5F9;'/>", unsafe_allow_html=True)

def render_tab_documentos(tender_id, cols_config):
    # Inyectamos CSS usando selectores estructurales estrictos para evitar fallos de renderizado
    st.markdown("""
        <style>
        /* Ocultar labels de inputs nativos */
        div[data-testid="stFileUploader"] label, 
        div[data-testid="stTextInput"] label, 
        div[data-testid="stSelectbox"] label {
            display: none !important;
        }

        /* --------------------------------------------------------
           1. CARDS PRINCIPALES (Fondo y Separación Visual)
           -------------------------------------------------------- */
        /* Panel Izquierdo: Gris muy claro para diferenciarlo */
        div[data-testid="column"]:nth-of-type(1) > div[data-testid="stVerticalBlock"] {
            background-color: #F8FAFC !important;
            border-radius: 12px !important;
            border: 1px solid #E5E7EB !important;
            padding: 24px !important;
            box-shadow: 0 1px 2px 0 rgba(0,0,0,0.03) !important;
        }
        
        /* Panel Derecho: Blanco puro */
        div[data-testid="column"]:nth-of-type(2) > div[data-testid="stVerticalBlock"] {
            background-color: #ffffff !important;
            border-radius: 12px !important;
            border: 1px solid #E5E7EB !important;
            padding: 24px !important;
            box-shadow: 0 1px 3px 0 rgba(0,0,0,0.04) !important;
        }

        /* --------------------------------------------------------
           2. DATA TABLE (Contenedor unificado)
           -------------------------------------------------------- */
        /* El contenedor de la tabla es el bloque vertical interno del Panel Derecho */
        div[data-testid="column"]:nth-of-type(2) > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            background-color: #ffffff !important;
            padding: 0 !important;
            margin-top: 24px !important;
            overflow: hidden !important;
        }
        
        /* Eliminar el espacio entre filas de Streamlit */
        div[data-testid="column"]:nth-of-type(2) > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div {
            gap: 0 !important;
        }
        
        /* Cabecera de la tabla (Primer bloque horizontal) */
        div[data-testid="column"]:nth-of-type(2) > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type {
            background-color: #F8FAFC !important;
            border-bottom: 1px solid #E2E8F0 !important;
            padding-top: 12px !important;
            padding-bottom: 12px !important;
            align-items: center !important;
        }

        /* --------------------------------------------------------
           3. COMPONENTES INTERNOS
           -------------------------------------------------------- */
        /* Uploader personalizado */
        div[data-testid="stFileUploadDropzone"] {
            background-color: #ffffff !important;
            border: 2px dashed #CBD5E1 !important;
            border-radius: 12px !important;
            padding: 30px 20px !important;
            text-align: center !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stFileUploadDropzone"]:hover {
            border-color: #3B82F6 !important;
            background-color: #EFF6FF !important;
        }
        div[data-testid="stFileUploadDropzone"] svg, 
        div[data-testid="stFileUploadDropzone"] small,
        div[data-testid="stFileUploadDropzone"] span {
            display: none !important;
        }
        div[data-testid="stFileUploadDropzone"]::before {
            content: "☁️";
            font-size: 36px;
            display: block;
            margin-bottom: 8px;
        }

        /* Botón de Guardar CTA */
        .stButton > button[kind="primary"] {
            background-color: #2563EB !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 10px 24px !important;
            border: none !important;
        }
        .stButton > button[kind="primary"]:disabled {
            background-color: #94A3B8 !important;
            opacity: 0.6 !important;
        }

        /* Botones de acción dentro de la tabla (Descargar) - Scoped con doc-dl-anchor */
        div.element-container:has(.doc-dl-anchor) {
            display: none !important;
            margin: 0 !important;
            padding: 0 !important;
            height: 0 !important;
        }
        div.element-container:has(.doc-dl-anchor) + div.element-container div[data-testid="stDownloadButton"] {
            display: flex !important;
            justify-content: flex-start !important;
            width: 100% !important;
        }
        div.element-container:has(.doc-dl-anchor) + div.element-container div[data-testid="stDownloadButton"] button {
            border: 1px solid #E2E8F0 !important;
            background: #ffffff !important;
            color: #64748B !important;
            padding: 0 !important;
            height: 32px !important;
            width: 32px !important;
            min-height: 32px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
            font-size: 16px !important;
            border-radius: 6px !important;
        }
        div.element-container:has(.doc-dl-anchor) + div.element-container div[data-testid="stDownloadButton"] button:hover {
            color: #2563EB !important;
            border-color: #2563EB !important;
            background-color: #EFF6FF !important;
        }
        div.element-container:has(.doc-dl-anchor) + div.element-container div[data-testid="stDownloadButton"] button p,
        div.element-container:has(.doc-dl-anchor) + div.element-container div[data-testid="stDownloadButton"] button div {
            margin: 0 !important;
            padding: 0 !important;
            font-size: 18px !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* Buscador / Selectores */
        div[data-testid="stTextInput"] input {
            background-color: #F8FAFC !important;
            border-color: #E2E8F0 !important;
            border-radius: 8px !important;
            font-size: 13px !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            background-color: #ffffff !important;
            border-color: #E2E8F0 !important;
            border-radius: 8px !important;
        }

        /* Ocultar el ancla para que no ocupe espacio y desalinee el primer botón */
        div.element-container:has(.pag-anchor) {
            display: none !important;
            margin: 0 !important;
            padding: 0 !important;
            height: 0 !important;
        }

        /* Botones Funcionales de Paginación (Mediante hermano adyacente exacto) */
        div.element-container:has(.pag-anchor) + div.element-container button {
            border: 1px solid #E2E8F0 !important;
            background-color: #ffffff !important;
            color: #64748B !important;
            padding: 0 !important;
            height: 32px !important;
            width: 32px !important;
            min-height: 0 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: none !important;
            font-size: 13px !important;
            border-radius: 6px !important;
        }
        div.element-container:has(.pag-anchor) + div.element-container button:hover {
            color: #2563EB !important;
            border-color: #2563EB !important;
        }
        /* Pagina Activa (Primary Button) */
        div.element-container:has(.pag-anchor) + div.element-container button[kind="primary"] {
            background-color: #2563EB !important;
            color: white !important;
            border: 1px solid #2563EB !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            padding: 0 !important;
            height: 32px !important;
            width: 32px !important;
            min-height: 0 !important;
            border-radius: 6px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div.element-container:has(.pag-anchor) + div.element-container button:disabled {
            opacity: 0.5 !important;
            cursor: not-allowed !important;
        }
        /* Centrar texto interno del boton */
        div.element-container:has(.pag-anchor) + div.element-container button p,
        div.element-container:has(.pag-anchor) + div.element-container button div {
            margin: 0 !important;
            padding: 0 !important;
            font-size: 13px !important;
            line-height: 1 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    docs_dir = os.path.join("data", "tenders", str(tender_id), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    docs = glob.glob(os.path.join(docs_dir, "*"))
    
    # Filtrado y Ordenamiento
    search_query = st.session_state.get(f"search_docs_{tender_id}", "").lower()
    sort_order = st.session_state.get(f"sort_docs_{tender_id}", "Más recientes")
    
    if search_query:
        docs = [d for d in docs if search_query in os.path.basename(d).lower()]
        
    if sort_order == "Más recientes":
        docs.sort(key=lambda x: os.path.getctime(x), reverse=True)
    elif sort_order == "Antiguos":
        docs.sort(key=lambda x: os.path.getctime(x), reverse=False)
    elif sort_order == "Nombre":
        docs.sort(key=lambda x: os.path.basename(x).lower())
    
    # Lógica de paginación de estado
    page_size = 4
    if "doc_page" not in st.session_state:
        st.session_state.doc_page = 1
    
    total_pages = max(1, ((len(docs) - 1) // page_size) + 1)
    if st.session_state.doc_page > total_pages:
        st.session_state.doc_page = total_pages
        
    start_idx = (st.session_state.doc_page - 1) * page_size
    end_idx = start_idx + page_size
    current_docs = docs[start_idx:end_idx]
    
    cols = st.columns([3, 7], gap="large")
    
    # ================== PANEL IZQUIERDO ==================
    with cols[0]:
        with st.container():
            st.markdown("""
                <h3 style='margin:0 0 4px 0; font-size:16px; font-weight:700; color:#0F172A;'>Subir nuevos documentos</h3>
                <p style='margin:0 0 24px 0; font-size:13px; color:#64748B; line-height:1.4;'>Arrastra y suelta tus archivos aquí o selecciónalos desde tu dispositivo.</p>
            """, unsafe_allow_html=True)
            
            uploaded_files = st.file_uploader("Upload", type=["pdf", "docx", "xlsx", "xls"], accept_multiple_files=True, key="docs_uploader")
            
            st.markdown("""
                <div style='text-align:center; margin-top: 16px; margin-bottom: 24px;'>
                    <div style='font-size:11px; color:#94A3B8; font-weight: 600; text-transform: uppercase;'>PDF, DOCX, XLSX, XLS</div>
                    <div style='font-size:11px; color:#94A3B8; margin-top:4px;'>Tamaño máximo por archivo: 200 MB</div>
                </div>
            """, unsafe_allow_html=True)
            
            disabled = not bool(uploaded_files)
            if st.button("Guardar e incluir", type="primary", use_container_width=True, disabled=disabled):
                save_uploaded_files(uploaded_files, tender_id)
                st.success("Archivos agregados exitosamente.")
                st.rerun()
                
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            if st.button("🕒 Historial de IA", use_container_width=True, help="Ver interacciones con la IA"):
                render_ia_history(tender_id)

    # ================== PANEL DERECHO ==================
    with cols[1]:
        with st.container():
            # Header
            head_c1, head_c2 = st.columns([2, 3], vertical_alignment="bottom")
            with head_c1:
                st.markdown("<h3 style='margin:0 0 2px 0; font-size:18px; font-weight:700; color:#0F172A;'>Archivos actuales</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:0; font-size:13px; color:#64748B;'>{len(docs)} documentos</p>", unsafe_allow_html=True)
            with head_c2:
                t1, t2, t3 = st.columns([2.5, 1.2, 1.5])
                with t1: st.text_input("Buscar", placeholder="🔍 Buscar documento...", key=f"search_docs_{tender_id}")
                with t2: st.button("Filtros", use_container_width=True)
                with t3: st.selectbox("Orden", ["Más recientes", "Nombre", "Antiguos"], key=f"sort_docs_{tender_id}")

            # --- CONTENEDOR DE LA TABLA ---
            with st.container():
                
                # CABECERA DE TABLA (Mismas proporciones que las filas para alineación perfecta)
                hc1, hc2 = st.columns([9.0, 1.0], vertical_alignment="center")
                with hc1:
                    st.markdown("""
                    <div style="display: flex; align-items: center; width: 100%; padding-left: 24px; font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">
                        <div style="flex: 5; padding-right: 15px;">Archivo</div>
                        <div style="flex: 1.5;">Tamaño</div>
                        <div style="flex: 2;">Subido el</div>
                    </div>
                    """, unsafe_allow_html=True)
                with hc2:
                    st.markdown("<div style='display: flex; justify-content: flex-start; width: 100%; font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;'>Acciones</div>", unsafe_allow_html=True)
                
                # FILAS DE TABLA
                if not docs:
                    st.markdown("<div style='padding: 60px 20px; text-align: center; color: #94A3B8; font-size: 14px; background: white;'>No hay documentos cargados en esta licitación.</div>", unsafe_allow_html=True)
                else:
                    for i, doc in enumerate(current_docs):
                        file_name = os.path.basename(doc)
                        file_size = os.path.getsize(doc) / 1024
                        dt = datetime.fromtimestamp(os.path.getctime(doc))
                        date_str = dt.strftime("%d/%m/%Y")
                        time_str = dt.strftime("%H:%M")
                        
                        ext = file_name.split('.')[-1].upper()
                        icon = "📄"
                        icon_bg = "#F1F5F9"
                        if ext == "PDF": 
                            icon = "📕"
                            icon_bg = "#FEF2F2"
                        elif ext in ["XLSX", "XLS"]: 
                            icon = "📗"
                            icon_bg = "#F0FDF4"
                        elif ext == "DOCX": 
                            icon = "📘"
                            icon_bg = "#EFF6FF"
                        
                        # FILA HÍBRIDA
                        r1, r2 = st.columns([9.0, 1.0], vertical_alignment="center")
                        
                        with r1:
                            st.markdown(f"""
                            <div style="display: flex; align-items: center; width: 100%; padding: 14px 0 14px 24px;">
                                <div style="flex: 5; display: flex; align-items: center; gap: 14px; min-width: 0; padding-right: 15px;">
                                    <div style="font-size: 18px; display:flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:8px; background-color:{icon_bg};">{icon}</div>
                                    <div style="min-width: 0; overflow: hidden;">
                                        <div style="font-size: 13px; font-weight: 600; color: #0F172A; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;" title="{file_name}">{file_name}</div>
                                        <div style="font-size: 11px; color: #64748B; font-weight: 500; margin-top: 2px;">{ext}</div>
                                    </div>
                                </div>
                                <div style="flex: 1.5; font-size: 13px; color: #475569; font-weight: 500;">{file_size:.0f} KB</div>
                                <div style="flex: 2; font-size: 13px; color: #0F172A;">{date_str}<br><span style="font-size: 11px; color: #94A3B8;">{time_str}</span></div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with r2:
                            st.markdown("<div class='doc-dl-anchor'></div>", unsafe_allow_html=True)
                            with open(doc, "rb") as f:
                                mime = "application/pdf" if ext=="PDF" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext=="DOCX" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                st.download_button("↓", data=f, file_name=file_name, mime=mime, key=f"dl_doc_{i}", help="Descargar")
                        
                        # Separador
                        st.markdown("<hr style='margin: 0; border: none; border-bottom: 1px solid #F1F5F9;'/>", unsafe_allow_html=True)

                # --- PAGINACIÓN FUNCIONAL ---
                if len(docs) > 4:
                    with st.container():
                        pc1, pc2 = st.columns([6, 4], vertical_alignment="center")
                        
                        with pc1:
                            # Controles de Paginación
                            btn_cols = st.columns([1, 1, 1, 1, 1, 1, 3]) 
                            
                            with btn_cols[0]:
                                st.markdown("<div class='pag-anchor'></div>", unsafe_allow_html=True)
                                if st.button("‹", key="prev_pg", disabled=(st.session_state.doc_page == 1)):
                                    st.session_state.doc_page -= 1
                                    st.rerun()
                                    
                            # Mostrar hasta 5 números
                            for idx, p in enumerate(range(1, min(6, total_pages + 1))):
                                with btn_cols[idx + 1]:
                                    st.markdown("<div class='pag-anchor'></div>", unsafe_allow_html=True)
                                    if st.button(str(p), key=f"pg_{p}", type="primary" if p == st.session_state.doc_page else "secondary"):
                                        st.session_state.doc_page = p
                                        st.rerun()
                                        
                            with btn_cols[min(6, total_pages + 1)]:
                                st.markdown("<div class='pag-anchor'></div>", unsafe_allow_html=True)
                                if st.button("›", key="next_pg", disabled=(st.session_state.doc_page == total_pages)):
                                    st.session_state.doc_page += 1
                                    st.rerun()
                                    
                        with pc2:
                            st.markdown(f"""
                            <div style="font-size: 12px; color: #64748B; display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 0px;">
                                Mostrando {start_idx + 1}–{min(end_idx, len(docs))} de {len(docs)} documentos
                                <div style="border: 1px solid #E2E8F0; padding: 4px 8px; border-radius: 6px; color: #0F172A; font-weight: 500; cursor: pointer;">4 ▾</div>
                            </div>
                            """, unsafe_allow_html=True)
