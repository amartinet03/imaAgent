import streamlit as st
from typing import List, Dict

class TenderMemory:
    """
    Gestiona el estado conversacional y los documentos de una licitación en la sesión actual.
    """
    @staticmethod
    def initialize_session_state():
        if "messages" not in st.session_state:
            st.session_state["messages"] = [
                {"role": "assistant", "content": "¡Hola! Soy Tender AI. Estoy listo para ayudarte con la nueva licitación. ¿Podrías proporcionarme los pliegos o la información inicial?"}
            ]
        
        if "tender_context" not in st.session_state:
            st.session_state["tender_context"] = {
                "documents": [],
                "terrain_visits": [],
                "client_answers": [],
                "current_stage": "recepcion", # recepcion, analisis, visitas, oferta
                "parsed_data": None
            }
            
    @staticmethod
    def add_message(role: str, content: str):
        st.session_state["messages"].append({"role": role, "content": content})
        
    @staticmethod
    def get_messages() -> List[Dict]:
        return st.session_state.get("messages", [])
        
    @staticmethod
    def update_context(key: str, value: any):
        if "tender_context" in st.session_state:
            if isinstance(st.session_state["tender_context"].get(key), list):
                st.session_state["tender_context"][key].append(value)
            else:
                st.session_state["tender_context"][key] = value

    @staticmethod
    def get_context() -> Dict:
        return st.session_state.get("tender_context", {})
