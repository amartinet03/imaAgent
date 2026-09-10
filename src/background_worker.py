import sys
import os
import concurrent.futures
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.models import update_tender_status
from src.ingestion.local_parser import process_file_to_langchain_docs
from src.core.analyzer import create_vector_store, analyze_full_tender
from src.outputs.word_generator import WordGenerator
from src.outputs.query_generator import QueryGenerator
import re

def process_tender(tender_id: int):
    try:
        from src.db.models import get_tender
        existing_tender = get_tender(tender_id)
        if not existing_tender:
            print("Licitación no encontrada.")
            return
            
        old_parsed_data = existing_tender.get("parsed_data") or {}
        sp_folder_id = old_parsed_data.get("sp_folder_id")
        tender_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'tenders', str(tender_id))
        docs_dir = os.path.join(tender_dir, 'docs')
        chroma_dir = os.path.join(tender_dir, 'chroma')
        
        if not os.path.exists(docs_dir):
            update_tender_status(tender_id, "ERROR", error_message="No se encontraron documentos.")
            return

        print(f"Iniciando procesamiento de Licitacion {tender_id}...")
        
        # 1. Leer y extraer texto de todos los documentos
        all_docs = []
        for filename in os.listdir(docs_dir):
            file_path = os.path.join(docs_dir, filename)
            if os.path.isfile(file_path):
                print(f"  Procesando archivo: {filename}")
                docs = process_file_to_langchain_docs(file_path)
                all_docs.extend(docs)

        if not all_docs:
            update_tender_status(tender_id, "ERROR", error_message="Los documentos estaban vacíos o no se pudieron leer.")
            return

        # 2. Ejecutar procesamiento en paralelo
        print("Ejecutando procesamiento IA (Nube) y Vectorial (Local) en paralelo...")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_vector = executor.submit(create_vector_store, all_docs, persist_directory=chroma_dir)
            future_analysis = executor.submit(analyze_full_tender, all_docs)
            
            try:
                future_vector.result()
            except Exception as e:
                print(f"Advertencia: Error al crear vectores: {e}")
                
            resultado = future_analysis.result()
            
        # 3. Guardar estado
        if isinstance(resultado, dict) and "error" not in resultado:
            print("Procesamiento completado con éxito.")
            
            # --- Generar Documentos Iniciales o Nuevas Revisiones ---
            try:
                import glob
                from src.db.models import add_message
                from src.integrations.ms365_client import MS365Client
                
                ms_client = MS365Client()
                
                # MERGE con datos viejos para no perder sp_folder_id ni otros seteos manuales
                parsed_data = resultado
                parsed_data['sp_folder_id'] = sp_folder_id
                
                cliente = parsed_data.get("metadata", {}).get("cliente", f"Licitacion_{tender_id}")
                safe_cliente = re.sub(r'[^A-Za-z0-9]+', '_', str(cliente))
                
                outputs_dir = os.path.join(tender_dir, 'outputs')
                os.makedirs(outputs_dir, exist_ok=True)
                
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ot_template = os.path.join(project_root, "templates", "OT_template.docx")
                rfi_template = os.path.join(project_root, "templates", "Consultas_Pliego_PAMPA_Obras_Civiles_Menores_PGSM.docx")
                
                # Calcular numero de revision
                ot_files = glob.glob(os.path.join(outputs_dir, "OT_*.docx"))
                rfi_files = glob.glob(os.path.join(outputs_dir, "Consultas_*.docx"))
                rev_ot = len(ot_files)
                rev_rfi = len(rfi_files)
                
                print(f"Generando documentos REV{rev_ot:02d}...")
                
                # 1. Oferta Técnica
                ot_name = f"OT_{tender_id}_{safe_cliente}_REV{rev_ot:02d}.docx"
                ot_path = os.path.join(outputs_dir, ot_name)
                WordGenerator().draft_technical_offer(
                    {"parsed_data": parsed_data}, 
                    ot_template, 
                    ot_path, 
                    metadata=parsed_data.get("metadata", {})
                )
                
                # 2. Consultas
                rfi_name = f"Consultas_Pliego_{safe_cliente}_REV{rev_rfi:02d}.docx"
                rfi_path = os.path.join(outputs_dir, rfi_name)
                QueryGenerator().generate_docx_from_json(
                    parsed_data, 
                    rfi_template, 
                    rfi_path
                )
                print(f"Documentos generados correctamente (REV{rev_ot:02d}).")
                
                # --- SUBIR A SHAREPOINT ---
                if sp_folder_id:
                    print("Subiendo nuevos documentos a SharePoint...")
                    user_email = os.getenv("MS365_MONITOR_EMAIL")
                    
                    with open(ot_path, "rb") as f:
                        ms_client.upload_file_to_user_drive(user_email, sp_folder_id, "OT", ot_name, f.read())
                        
                    with open(rfi_path, "rb") as f:
                        ms_client.upload_file_to_user_drive(user_email, sp_folder_id, "Elementos de estudio", rfi_name, f.read())
                    print("Documentos subidos a SharePoint exitosamente.")
                
                # Notificar en el chat si es una actualización
                if rev_ot > 0 or rev_rfi > 0:
                    add_message(tender_id, "system", f"🔔 **Nuevos Documentos Recibidos y Analizados**. Se han generado nuevas versiones de la Oferta Técnica (REV{rev_ot:02d}) y Consultas (REV{rev_rfi:02d}) considerando las nuevas aclaraciones/circulares ingresadas. Por favor, revísalas en sus pestañas correspondientes.")
                    
            except Exception as e:
                print(f"Error generando documentos: {e}")
                # Continuamos de todos modos para que el estado sea COMPLETADO
            # -------------------------------------------
            
            update_tender_status(tender_id, "COMPLETADO", parsed_data=resultado)
            
            # Enviar notificación por correo
            try:
                from src.integrations.notifier import notify_analysis_completed
                user_email = os.getenv("NOTIFY_EMAIL", "tu_correo@imaservicios.com")
                notify_analysis_completed(user_email, tender_id, cliente)
            except Exception as e:
                print(f"No se pudo enviar la notificación: {e}")

        else:
            print(f"Error en el análisis de Claude: {resultado}")
            update_tender_status(tender_id, "ERROR", error_message=str(resultado))
            
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Fallo critico en background worker:\n{error_trace}")
        update_tender_status(tender_id, "ERROR", error_message=str(e))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python background_worker.py <tender_id>")
        sys.exit(1)
        
    tender_id_arg = int(sys.argv[1])
    process_tender(tender_id_arg)
