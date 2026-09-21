import streamlit as st
import os
import glob
import time
import re
import streamlit_antd_components as sac
from src.ui.components import render_versions_list
from src.ui.theme import render_info_list_item
from src.outputs.excel_generator import ExcelGenerator

def render_tab_eco(tender_id, parsed_data, outputs_dir, safe_cliente, cols_config):
    cols_eco = st.columns(cols_config, gap="large")
    
    with cols_eco[0]:
        with st.container():
            st.markdown("### Base para Costeo Económico")
            st.markdown("Excel base con los requerimientos extraídos.")
            render_info_list_item("💰", "Moneda", "No especificada")
            render_info_list_item("📊", "Formato de Cotización", "Excel Estándar IMA")
            
            st.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)
            st.markdown("#### 🔍 Verificación de Costos")
            st.markdown("<p style='font-size: 14px; margin-bottom: 0;'>Sube el Excel cotizado para que la IA detecte errores frente al pliego.</p>", unsafe_allow_html=True)
            uploaded_cost_file = st.file_uploader("Subir Excel", type=["xlsx"], key="cost_upload")
            
            if uploaded_cost_file:
                if st.button("Analizar 🤖", type="secondary", use_container_width=True):
                    with st.spinner("Comparando Excel..."):
                        # Guardar temporalmente sanitizando el nombre
                        safe_base = os.path.basename(uploaded_cost_file.name)
                        safe_base = re.sub(r'[^a-zA-Z0-9_.\-]', '_', safe_base)
                        temp_path = os.path.join(outputs_dir, f"TEMP_{safe_base}")
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_cost_file.getbuffer())
                            
                        try:
                            from src.core.analyzer import get_anthropic_api_key
                            from langchain_anthropic import ChatAnthropic
                            
                            llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", anthropic_api_key=get_anthropic_api_key())
                            generator = ExcelGenerator(llm_client=llm)
                            
                            report = generator.validate_cost_excel({"parsed_data": parsed_data}, temp_path)
                            
                            st.session_state[f'cost_report_{tender_id}'] = report
                            
                            # Subir archivo cotizado a SharePoint para respaldo
                            sp_folder_id = parsed_data.get("sp_folder_id")
                            if sp_folder_id:
                                try:
                                    from src.integrations.ms365_client import MS365Client
                                    ms_client = MS365Client()
                                    user_email = os.getenv("MS365_MONITOR_EMAIL")
                                    ms_client.upload_file_to_user_drive(user_email, sp_folder_id, "OC", uploaded_cost_file.name, uploaded_cost_file.getvalue())
                                except Exception as e:
                                    pass # Fallo silenciado, la validacion importa mas aqui
                                    
                        except Exception as e:
                            st.error(f"Error en validación: {e}")
                        finally:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                                
            if f'cost_report_{tender_id}' in st.session_state:
                st.info("Resultado de la Validación:")
                st.markdown(st.session_state[f'cost_report_{tender_id}'])

            st.markdown("<hr style='margin-top: 1rem; margin-bottom: 1rem;'/>", unsafe_allow_html=True)
            st.markdown("#### 💬 Consultas sobre Costos y Pliego")
            
            # Interfaz de chat simple
            if f"chat_eco_{tender_id}" not in st.session_state:
                st.session_state[f"chat_eco_{tender_id}"] = []
                
            for msg in st.session_state[f"chat_eco_{tender_id}"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
            if prompt := st.chat_input("Pregunta sobre tu cotización o el pliego..."):
                st.session_state[f"chat_eco_{tender_id}"].append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                    
                with st.chat_message("assistant"):
                    with st.spinner("Analizando..."):
                        try:
                            from src.core.analyzer import get_anthropic_api_key
                            from langchain_anthropic import ChatAnthropic
                            llm_chat = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", anthropic_api_key=get_anthropic_api_key())
                            
                            context = f"Eres un asistente experto validando costos de licitaciones.\nDatos extraídos del pliego: {parsed_data}\n\nPregunta del usuario: {prompt}"
                            response = llm_chat.invoke(context).content
                            st.markdown(response)
                            st.session_state[f"chat_eco_{tender_id}"].append({"role": "assistant", "content": response})
                        except Exception as e:
                            st.error(f"Error: {e}")

    with cols_eco[1]:
        with st.container():
            st.markdown("### Progreso del Documento Actual")
            eco_files = glob.glob(os.path.join(outputs_dir, "Costos_*.xlsx"))
            
            total_versions = len(eco_files) if len(eco_files) > 0 else 1
            
            sac.steps(
                items=[sac.StepsItem(title=f"REV{i:02d}", description="Actual" if i == total_versions - 1 else "Borrador") for i in range(total_versions)],
                index=total_versions - 1,
                color='#2563EB',
                placement='vertical',
                key='steps_eco'
            )
            
            st.markdown("### Versiones del Documento")
            render_versions_list(eco_files, "eco")
            
            if st.button("Generar Excel de Trabajo ✨", type="primary", use_container_width=True, key="gen_eco"):
                try:
                    with st.spinner("Ensamblando Excel con requerimientos de la IA..."):
                        rev_num = len(eco_files)
                        out_name = f"Costos_{tender_id}_{safe_cliente}_REV{rev_num:02d}.xlsx"
                        output_path = os.path.join(outputs_dir, out_name)
                        
                        try:
                            from src.core.analyzer import get_anthropic_api_key
                            from langchain_anthropic import ChatAnthropic
                            llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", anthropic_api_key=get_anthropic_api_key())
                            generator = ExcelGenerator(llm_client=llm)
                        except Exception as e:
                            st.warning("No se pudo iniciar LLM para búsqueda de precios. Fallback a generador simple.")
                            generator = ExcelGenerator()
                            
                        template_path = os.path.join(os.getcwd(), "templates", "plantilla_costeo.xlsx")
                        generator.generate_cost_excel({"parsed_data": parsed_data, "tender_id": tender_id}, template_path, output_path)
                        
                        # Subir a SharePoint
                        sp_folder_id = parsed_data.get("sp_folder_id")
                        if sp_folder_id:
                            try:
                                from src.integrations.ms365_client import MS365Client
                                ms_client = MS365Client()
                                user_email = os.getenv("MS365_MONITOR_EMAIL")
                                with open(output_path, "rb") as f:
                                    ms_client.upload_file_to_user_drive(user_email, sp_folder_id, "OC", out_name, f.read())
                            except Exception as e:
                                st.warning(f"Excel generado localmente pero falló la subida a SharePoint: {e}")
                                
                    st.success(f"¡Versión REV{rev_num:02d} generada y subida a SharePoint!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generando Excel: {e}")
