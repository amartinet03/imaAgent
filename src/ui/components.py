import streamlit as st
import os
import time

def format_date(timestamp):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))

def render_versions_list(files, prefix):
    if not files:
        st.write("No hay versiones generadas todavía.")
        return
        
    # Table Header
    h1, h2, h3, h4 = st.columns([1.5, 1.2, 1.5, 1.5], gap="small")
    header_style = "font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;"
    h1.markdown(f"<div style='{header_style}'>Versión</div>", unsafe_allow_html=True)
    h2.markdown(f"<div style='{header_style}'>Estado</div>", unsafe_allow_html=True)
    h3.markdown(f"<div style='{header_style}'>Fecha</div>", unsafe_allow_html=True)
    h4.markdown(f"<div style='{header_style}'>Acciones</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 10px 0; border-color: #E2E8F0; border-width: 2px;'/>", unsafe_allow_html=True)
        
    files.sort(key=os.path.getctime)
    total = len(files)
    
    for i, file_path in enumerate(files):
        rev_num = i
        is_latest = (i == total - 1)
        file_name = os.path.basename(file_path)
        date_str = format_date(os.path.getctime(file_path))
        
        status_html = '<span style="color:#F59E0B;background:#FEF3C7;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">En revisión</span>' if is_latest else '<span style="color:#64748B;background:#F1F5F9;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">Borrador</span>'
        
        c1, c2, c3, c4 = st.columns([1.5, 1.2, 1.5, 1.5], gap="small")
        with c1:
            st.markdown(f"<div style='font-size:13px; font-weight:600; color:#2563EB; margin-top: 6px;'>REV{rev_num:02d} {'(Actual)' if is_latest else ''}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='margin-top: 6px;'>{status_html}</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div style='font-size:12px; color:#64748B; margin-top: 6px;'>{date_str}</div>", unsafe_allow_html=True)
        with c4:
            with open(file_path, "rb") as f:
                ext = file_name.split('.')[-1]
                mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext == 'docx' else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                st.download_button("Descargar", data=f, file_name=file_name, mime=mime, key=f"dl_{prefix}_{i}", use_container_width=True)
        st.markdown("<hr style='margin: 8px 0; border-color: #F1F5F9;'/>", unsafe_allow_html=True)

def save_uploaded_files(uploaded_files, tender_id):
    import re
    docs_dir = os.path.join("data", "tenders", str(tender_id), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    for file in uploaded_files:
        # Sanitizar nombre de archivo para evitar path traversal
        raw_name = os.path.basename(file.name)
        safe_name = re.sub(r'[^a-zA-Z0-9_.\-\sáéíóúÁÉÍÓÚñÑ()]', '_', raw_name).strip()
        if not safe_name:
            safe_name = f"doc_{int(time.time())}.bin"
        file_path = os.path.join(docs_dir, safe_name)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
