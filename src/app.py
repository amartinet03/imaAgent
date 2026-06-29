import streamlit as st
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.local_parser import process_file_to_langchain_docs
from src.core.analyzer import analyze_cross_document_conflicts

def main():
    st.set_page_config(page_title="Tender AI - Gestión de Licitaciones", layout="wide")
    
    with st.sidebar:
        st.title("Tender AI")
        st.subheader("Menú Principal")
        st.button("Licitaciones Activas", use_container_width=True)
        st.button("Base de Conocimiento", use_container_width=True)
        st.button("Configuración", use_container_width=True)
        
    st.title("Gestión de Licitaciones 🏢")
    st.markdown("Sube pliegos, especificaciones, anexos (PDF, Word, Excel).")
    
    # Subida Múltiple
    uploaded_files = st.file_uploader("Sube los archivos aquí (Drag & Drop)", type=["pdf", "docx", "xlsx", "xls"], accept_multiple_files=True)
    
    if uploaded_files:
        st.success(f"Se cargaron {len(uploaded_files)} archivos listos para procesar.")
        
        if st.button("Procesar e Indexar Documentos", type="primary"):
            all_docs = []
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                st.text(f"Procesando: {file.name}...")
                docs = process_file_to_langchain_docs(file)
                all_docs.extend(docs)
                progress_bar.progress((i + 1) / len(uploaded_files))
                
            st.session_state['all_docs'] = all_docs
            st.success(f"¡Procesamiento completo! {len(all_docs)} fragmentos generados en total.")
        
        st.divider()
        st.write("### Análisis Avanzado (Requiere Procesamiento Previo)")
        
        if st.button("🕵️ Analizar Incongruencias (Cross-Check)"):
            if 'all_docs' in st.session_state and st.session_state['all_docs']:
                with st.spinner("Ejecutando Map-Reduce con IA para detectar contradicciones cruzadas..."):
                    resultado = analyze_cross_document_conflicts(st.session_state['all_docs'])
                    st.warning("### Reporte de Incongruencias Detectadas")
                    st.write(resultado)
            else:
                st.error("Primero debes hacer clic en 'Procesar e Indexar Documentos'.")
                
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.button("Generar Consultas Técnicas", use_container_width=True)
        with col2:
            st.button("Borrador Oferta Técnica", use_container_width=True)

if __name__ == "__main__":
    main()
