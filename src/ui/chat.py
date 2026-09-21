import streamlit as st
import os
import glob
import re
import time
from streamlit_autorefresh import st_autorefresh

from src.db.models import get_messages, add_message
from src.core.chat_worker import is_chat_job_running, start_chat_background_job, get_chat_job_info


@st.dialog("✨ Asistente IA", width="large")
def render_chat_interface(tender_id, parsed_data, chat_type):
    """
    Pop-up interactivo del Asistente IA.
    Ejecuta las modificaciones y la generación de documentos Word en segundo plano,
    permitiendo al usuario cerrar la ventana o navegar libremente mientras el documento
    se ensambla automáticamente.
    """
    job_running = is_chat_job_running(tender_id, chat_type)

    header_title = "Oferta Técnica (OT)" if chat_type == "OT" else "Consultas al Pliego (RFI)"
    st.markdown(
        f"<p style='font-size: 13.5px; color: #64748B; margin-top:-10px; margin-bottom: 12px;'>"
        f"Sección activa: <strong>{header_title}</strong>. Sugiere cambios al documento (ej: 'Agrega un supervisor electromecánico' o 'Ajusta el plazo a 30 días')."
        f"</p>",
        unsafe_allow_html=True
    )

    # Si hay una tarea ejecutándose en segundo plano, refrescar cada 2.5s para mostrar la respuesta
    if job_running:
        st_autorefresh(interval=2500, key=f"dialog_refresh_{tender_id}_{chat_type}")
        job_info = get_chat_job_info(tender_id, chat_type) or {}
        last_prompt = job_info.get("prompt", "")
        prompt_snippet = f": *\"{last_prompt[:60]}...\"*" if last_prompt else ""

        st.markdown(
            f"""
            <div style="background-color: #EFF6FF; border: 1.5px solid #93C5FD; border-left: 4px solid #2563EB; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="font-size: 0.88rem; color: #1E40AF; font-weight: 700;">
                        🤖 Generando nueva versión en segundo plano{prompt_snippet}
                    </div>
                    <span style="background-color: #DBEAFE; color: #1D4ED8; font-size: 0.72rem; font-weight: 800; padding: 2px 8px; border-radius: 12px;">
                        EN PROCESO
                    </span>
                </div>
                <div style="font-size: 0.8rem; color: #3B82F6; margin-top: 4px;">
                    Podés cerrar este pop-up tranquilamente; el documento continuará ensamblándose en segundo plano y se creará la nueva versión automáticamente.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Historial de mensajes
    messages = get_messages(tender_id, chat_type=chat_type)
    if not messages:
        msg = f"¡Hola! Soy tu asistente de IA. He extraído la información para la sección de {header_title}. ¿Hay algo que desees ajustar antes de generar una nueva versión?"
        add_message(tender_id, "assistant", msg, chat_type=chat_type)
        messages = get_messages(tender_id, chat_type=chat_type)

    # Mostrar mensajes en contenedor con scroll
    with st.container():
        for msg in messages:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

    # Entrada de chat
    if job_running:
        st.markdown(
            "<div style='text-align: center; color: #94A3B8; font-size: 0.82rem; padding: 10px 0;'>"
            "⏳ Hay una generación de versión en curso. Esperá a que finalice para enviar otra instrucción."
            "</div>",
            unsafe_allow_html=True
        )
    else:
        if prompt := st.chat_input("Escribe tu instrucción aquí...", key=f"chat_{chat_type}"):
            if prompt.strip():
                clean_prompt = prompt.strip()
                # Registrar mensaje del usuario en la base de datos
                add_message(tender_id, "user", clean_prompt, chat_type=chat_type)

                # Lanzar el proceso en segundo plano (hilo independiente)
                started = start_chat_background_job(tender_id, chat_type, clean_prompt)
                if started:
                    st.toast("🚀 Instrucción enviada. El documento se está generando en segundo plano.", icon="🤖")
                st.rerun()
