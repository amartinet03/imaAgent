import streamlit as st
import os
import glob
import re
import time

from src.db.models import get_messages, add_message, update_tender_parsed_data
from src.core.chat_modifier import modify_json_with_chat
from src.outputs.word_generator import WordGenerator
from src.outputs.query_generator import QueryGenerator

@st.dialog("✨ Asistente IA", width="large")
def render_chat_interface(tender_id, parsed_data, chat_type):
    st.markdown("<p style='font-size: 14px; margin-top:-10px;'>Sugiere cambios al documento (ej: 'Agrega un supervisor').</p>", unsafe_allow_html=True)
    
    messages = get_messages(tender_id, chat_type=chat_type)
    if not messages:
        msg = f"¡Hola! Soy tu asistente de IA. He extraído la información para la sección {chat_type}. ¿Hay algo que desees ajustar antes de generar una nueva versión?"
        add_message(tender_id, "assistant", msg, chat_type=chat_type)
        messages = get_messages(tender_id, chat_type=chat_type)
        
    for msg in messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
            st.write(msg["content"])
            
    if prompt := st.chat_input("Escribe tu instrucción aquí...", key=f"chat_{chat_type}"):
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        add_message(tender_id, "user", prompt, chat_type=chat_type)
        
        with st.spinner("Aplicando cambios y generando nueva versión..."):
            history = get_messages(tender_id, chat_type=chat_type)
            updated_data = modify_json_with_chat(parsed_data, history, prompt, chat_type=chat_type)
            update_tender_parsed_data(tender_id, updated_data)
            
            try:
                # El directorio base es asumiendo que estamos en src/ui/chat.py
                tender_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'tenders', str(tender_id))
                outputs_dir = os.path.join(tender_dir, 'outputs')
                cliente = updated_data.get("metadata", {}).get("cliente", f"Licitacion_{tender_id}")
                safe_cliente = re.sub(r'[^A-Za-z0-9]+', '_', str(cliente))
                
                rev_num = 0
                if chat_type == "OT":
                    ot_files = glob.glob(os.path.join(outputs_dir, "OT_*.docx"))
                    rev_num = len(ot_files)
                    out_name = f"OT_{tender_id}_{safe_cliente}_REV{rev_num:02d}.docx"
                    WordGenerator().draft_technical_offer({"parsed_data": updated_data}, "templates/OT_template.docx", os.path.join(outputs_dir, out_name), metadata=updated_data.get("metadata", {}))
                elif chat_type == "CONSULTAS":
                    rfi_files = glob.glob(os.path.join(outputs_dir, "Consultas_*.docx"))
                    rev_num = len(rfi_files)
                    out_name = f"Consultas_Pliego_{safe_cliente}_REV{rev_num:02d}.docx"
                    QueryGenerator().generate_docx_from_json(updated_data, "templates/Consultas_Pliego_PAMPA_Obras_Civiles_Menores_PGSM.docx", os.path.join(outputs_dir, out_name))
                
                resp = f"¡Hecho! He aplicado tus instrucciones y he generado automáticamente la nueva versión (REV{rev_num:02d}) del documento."
            except Exception as e:
                resp = f"He aplicado los cambios en los datos, pero ocurrió un error al generar el documento: {e}"
        
        with st.chat_message("assistant", avatar="🤖"):
            st.write(resp)
        add_message(tender_id, "assistant", resp, chat_type=chat_type)
        time.sleep(1)
        st.rerun()
