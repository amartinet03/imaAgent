import streamlit as st
import os
import glob
import time
import streamlit_antd_components as sac
from src.ui.chat import render_chat_interface
from src.ui.components import render_versions_list
from src.outputs.query_generator import QueryGenerator

def render_tab_rfi(tender_id, parsed_data, outputs_dir, safe_cliente, cols_config):
    cols_rfi = st.columns(cols_config, gap="large")
    
    with cols_rfi[0]:
        with st.container():
            st.markdown("### Consultas Detectadas")
            
            inconsistencias_count = len(parsed_data.get("inconsistencias", []))
            consultas_count = len(parsed_data.get("consultas_generales", []))
            
            st.info(f"Se han detectado **{inconsistencias_count} inconsistencias** y **{consultas_count} consultas generales** en los pliegos.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✨ Asistente IA", use_container_width=True, key="ai_rfi"):
                render_chat_interface(tender_id, parsed_data, "CONSULTAS")
    with cols_rfi[1]:
        with st.container():
            st.markdown("### Progreso del Documento Actual")
            rfi_files = glob.glob(os.path.join(outputs_dir, "Consultas_*.docx"))
            
            total_versions = len(rfi_files) if len(rfi_files) > 0 else 1
            
            sac.steps(
                items=[sac.StepsItem(title=f"REV{i:02d}", description="Actual" if i == total_versions - 1 else "Borrador") for i in range(total_versions)],
                index=total_versions - 1,
                color='#2563EB',
                placement='vertical',
                key='steps_rfi'
            )
            
            st.markdown("### Versiones del Documento")
            render_versions_list(rfi_files, "rfi")
            
            if st.button("Generar nueva versión con cambios ✨", type="primary", use_container_width=True, key="gen_rfi"):
                with st.spinner("Ensamblando nueva revisión..."):
                    try:
                        rev_num = len(rfi_files)
                        out_name = f"Consultas_Pliego_{safe_cliente}_REV{rev_num:02d}.docx"
                        res = QueryGenerator().generate_docx_from_json(parsed_data, "templates/Consultas_Pliego_PAMPA_Obras_Civiles_Menores_PGSM.docx", os.path.join(outputs_dir, out_name))
                        if res.startswith("Error"):
                            st.error(res)
                        else:
                            st.success(f"¡Versión REV{rev_num:02d} generada!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al generar consultas: {e}")
