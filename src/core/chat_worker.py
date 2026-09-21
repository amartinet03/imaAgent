import os
import glob
import re
import time
import threading
from typing import Dict, Optional

# Registro thread-safe de tareas en segundo plano: {(tender_id, chat_type): dict_info}
_ACTIVE_JOBS: Dict[tuple, dict] = {}
_JOBS_LOCK = threading.Lock()


def is_chat_job_running(tender_id: int, chat_type: Optional[str] = None) -> bool:
    """
    Verifica si hay un proceso de generación por IA en segundo plano activo para la licitación.
    Si chat_type se especifica ('OT' o 'CONSULTAS'), comprueba únicamente esa sección.
    """
    with _JOBS_LOCK:
        if chat_type:
            job = _ACTIVE_JOBS.get((tender_id, chat_type))
            return job is not None and job.get("status") == "running"
        return any(
            t_id == tender_id and job.get("status") == "running"
            for (t_id, _), job in _ACTIVE_JOBS.items()
        )


def get_chat_job_info(tender_id: int, chat_type: str) -> Optional[dict]:
    """Obtiene la información de la tarea en ejecución para (tender_id, chat_type)."""
    with _JOBS_LOCK:
        return _ACTIVE_JOBS.get((tender_id, chat_type))


def _set_chat_job_status(tender_id: int, chat_type: str, status: str, **kwargs):
    """Actualiza el estado de la tarea en el registro."""
    with _JOBS_LOCK:
        key = (tender_id, chat_type)
        if status == "finished":
            _ACTIVE_JOBS.pop(key, None)
        else:
            if key not in _ACTIVE_JOBS:
                _ACTIVE_JOBS[key] = {}
            _ACTIVE_JOBS[key].update({"status": status, **kwargs})


def _execute_chat_generation(tender_id: int, chat_type: str, prompt: str):
    """
    Lógica de ejecución en segundo plano para:
    1. Modificar parsed_data con la IA (Claude Anthropic) a partir de la instrucción.
    2. Guardar datos actualizados en la base de datos SQLite.
    3. Ensamblar automáticamente la nueva versión (REVxx) del documento Word (OT o Consultas).
    4. Sincronizar la nueva versión en SharePoint si está configurado.
    5. Registrar el mensaje de éxito o error en el chat para el usuario.
    """
    try:
        from src.db.models import get_tender, get_messages, add_message, update_tender_parsed_data
        from src.core.chat_modifier import modify_json_with_chat
        from src.outputs.word_generator import WordGenerator
        from src.outputs.query_generator import QueryGenerator

        _set_chat_job_status(tender_id, chat_type, "running", prompt=prompt, start_time=time.time())

        # 1. Obtener datos actuales del pliego y mensajes
        tender = get_tender(tender_id)
        if not tender:
            raise ValueError(f"No se encontró la licitación con ID {tender_id}")

        parsed_data = tender.get("parsed_data", {})
        history = get_messages(tender_id, chat_type=chat_type)

        # 2. Modificar JSON con el LLM
        print(f"[Chat Worker] Procesando instrucción en segundo plano para Licitación {tender_id} ({chat_type}): '{prompt}'")
        updated_data = modify_json_with_chat(parsed_data, history, prompt, chat_type=chat_type)
        update_tender_parsed_data(tender_id, updated_data)

        # 3. Determinar rutas y nombres de archivo para la nueva versión
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        tender_dir = os.path.join(repo_root, "data", "tenders", str(tender_id))
        outputs_dir = os.path.join(tender_dir, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)

        cliente = updated_data.get("metadata", {}).get("cliente", f"Licitacion_{tender_id}")
        safe_cliente = re.sub(r'[^A-Za-z0-9]+', '_', str(cliente))

        rev_num = 0
        out_name = ""

        # 4. Generación automática del documento Word correspondiente
        if chat_type == "OT":
            ot_files = glob.glob(os.path.join(outputs_dir, "OT_*.docx"))
            rev_num = len(ot_files)
            out_name = f"OT_{tender_id}_{safe_cliente}_REV{rev_num:02d}.docx"
            out_path = os.path.join(outputs_dir, out_name)
            template_path = os.path.join(repo_root, "templates", "OT_template.docx")

            print(f"[Chat Worker] Ensamblando nueva versión OT: {out_name}")
            WordGenerator().draft_technical_offer(
                {"parsed_data": updated_data},
                template_path,
                out_path,
                metadata=updated_data.get("metadata", {})
            )

        elif chat_type == "CONSULTAS":
            rfi_files = glob.glob(os.path.join(outputs_dir, "Consultas_*.docx"))
            rev_num = len(rfi_files)
            out_name = f"Consultas_Pliego_{safe_cliente}_REV{rev_num:02d}.docx"
            out_path = os.path.join(outputs_dir, out_name)
            template_path = os.path.join(repo_root, "templates", "Consultas_Pliego_PAMPA_Obras_Civiles_Menores_PGSM.docx")

            print(f"[Chat Worker] Ensamblando nueva versión Consultas: {out_name}")
            QueryGenerator().generate_docx_from_json(updated_data, template_path, out_path)

        # 5. Sincronización automática con SharePoint (si existe carpeta configurada)
        sp_folder_id = updated_data.get("sp_folder_id") or updated_data.get("metadata", {}).get("sp_folder_id")
        if sp_folder_id and out_name:
            try:
                from src.integrations.ms365_client import MS365Client
                ms_client = MS365Client()
                user_email = os.getenv("MS365_MONITOR_EMAIL")
                if user_email:
                    folder_sub = "ET" if chat_type == "OT" else "AC"
                    file_path = os.path.join(outputs_dir, out_name)
                    with open(file_path, "rb") as f:
                        ms_client.upload_file_to_user_drive(user_email, sp_folder_id, folder_sub, out_name, f.read())
                    print(f"[Chat Worker] Archivo {out_name} subido exitosamente a SharePoint (/{folder_sub})")
            except Exception as sp_err:
                print(f"[Chat Worker] Nota: Documento generado localmente. SharePoint no disponible: {sp_err}")

        # 6. Registrar confirmación en el historial del chat
        success_msg = (
            f"✅ ¡He aplicado tus instrucciones y generado automáticamente la nueva versión **REV{rev_num:02d}**!\n\n"
            f"📄 **Documento generado:** `{out_name}`\n"
            f"✏️ **Cambios incorporados:** *\"{prompt}\"*\n\n"
            f"El archivo ya está listo para descargar y consultar en la lista de versiones."
        )
        add_message(tender_id, "assistant", success_msg, chat_type=chat_type)
        print(f"[Chat Worker] Proceso en segundo plano finalizado con éxito para Licitación {tender_id} ({chat_type}) -> REV{rev_num:02d}")

    except Exception as e:
        print(f"[Chat Worker] Error en generación de documento en segundo plano: {e}")
        try:
            from src.db.models import add_message
            err_msg = f"❌ Ocurrió un inconveniente al procesar tu solicitud en segundo plano: {str(e)}"
            add_message(tender_id, "assistant", err_msg, chat_type=chat_type)
        except Exception:
            pass
    finally:
        _set_chat_job_status(tender_id, chat_type, "finished")


def start_chat_background_job(tender_id: int, chat_type: str, prompt: str) -> bool:
    """
    Inicia la tarea de IA en segundo plano en un hilo independiente (daemon=True).
    Retorna True si la tarea inició o False si ya había una en curso para ese tipo.
    """
    if is_chat_job_running(tender_id, chat_type):
        return False

    _set_chat_job_status(tender_id, chat_type, "running", prompt=prompt, start_time=time.time())
    thread = threading.Thread(
        target=_execute_chat_generation,
        args=(tender_id, chat_type, prompt),
        daemon=True
    )
    thread.start()
    return True
