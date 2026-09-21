import streamlit as st
import os
import glob
import time
import streamlit_antd_components as sac
from src.ui.chat import render_chat_interface
from src.ui.components import render_versions_list
from src.outputs.word_generator import WordGenerator
from src.core.chat_worker import is_chat_job_running

def render_tab_ot(tender_id, parsed_data, outputs_dir, safe_cliente, cols_config):
    cols = st.columns(cols_config, gap="large")
    ot_running = is_chat_job_running(tender_id, "OT")
    
    with cols[0]:
        with st.container():
            st.markdown("### Información de la OT")
            
            cliente_nombre = parsed_data.get("metadata", {}).get("cliente", "N/A")
            planta = parsed_data.get("metadata", {}).get("planta", "N/A")
            proceso = parsed_data.get("metadata", {}).get("proceso", "N/A")
            
            info_html = f"""
            <div style="border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 15px; background: #F8FAFC; font-size: 12px; color: #475569; display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;">
                    <strong style="white-space: nowrap; margin-right: 10px;">🏢 Cliente:</strong> <span style="color: #0F172A; font-weight: 500; text-align: right; max-width: 65%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{cliente_nombre}">{cliente_nombre}</span>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;">
                    <strong style="white-space: nowrap; margin-right: 10px;">🏭 Planta:</strong> <span style="color: #0F172A; font-weight: 500; text-align: right; max-width: 65%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{planta}">{planta}</span>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;">
                    <strong style="white-space: nowrap; margin-right: 10px;">📄 Licitación:</strong> <span style="color: #0F172A; font-weight: 500; text-align: right; max-width: 65%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{proceso}">{proceso}</span>
                </div>
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;">
                    <strong style="white-space: nowrap; margin-right: 10px;">👤 Responsable:</strong> <span style="color: #0F172A; font-weight: 500; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Sebastien Martinet</span>
                </div>
            </div>
            """
            st.markdown(info_html, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            btn_label = "✨ Asistente IA ⏳ (Generando versión...)" if ot_running else "✨ Asistente IA"
            if st.button(btn_label, use_container_width=True, key="ai_ot"):
                render_chat_interface(tender_id, parsed_data, "OT")
            
    with cols[1]:
        with st.container():
            st.markdown("### Progreso del Documento Actual")
            if ot_running:
                st.markdown(
                    "<div style='background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 6px 12px; font-size: 12px; color: #1D4ED8; margin-bottom: 10px;'>"
                    "⏳ <strong>Generando nueva versión (REV) con IA en segundo plano...</strong>"
                    "</div>",
                    unsafe_allow_html=True
                )
            ot_files = glob.glob(os.path.join(outputs_dir, "OT_*.docx"))
            
            total_versions = len(ot_files) if len(ot_files) > 0 else 1
            
            sac.steps(
                items=[sac.StepsItem(title=f"REV{i:02d}", description="Actual" if i == total_versions - 1 else "Borrador") for i in range(total_versions)],
                index=total_versions - 1,
                color='#2563EB',
                placement='vertical',
                key='steps_ot'
            )
            
            st.markdown("### Versiones del Documento")
            render_versions_list(ot_files, "ot")
            
            if st.button("Generar nueva versión con cambios ✨", type="primary", use_container_width=True, key="gen_ot"):
                with st.spinner("Ensamblando nueva revisión..."):
                    try:
                        rev_num = len(ot_files)
                        out_name = f"OT_{tender_id}_{safe_cliente}_REV{rev_num:02d}.docx"
                        WordGenerator().draft_technical_offer({"parsed_data": parsed_data}, "templates/OT_template.docx", os.path.join(outputs_dir, out_name), metadata=parsed_data.get("metadata", {}))
                        st.success(f"¡Versión REV{rev_num:02d} generada!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
