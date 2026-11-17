import json
import re
from langchain_core.prompts import PromptTemplate

def modify_json_with_chat(current_json: dict, chat_history: list, user_instruction: str, chat_type: str = 'OT') -> dict:
    """
    Modifica el JSON de parsed_data basándose en la instrucción del usuario.
    """
    # Excluimos listas muy largas para no confundir al LLM a menos que estemos editándolas
    working_json = current_json.copy()
    
    json_str = json.dumps(working_json, ensure_ascii=False, indent=2)
    history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history[-5:]]) # Últimos 5 mensajes para contexto
    
    context_rules = ""
    if chat_type == 'OT':
        context_rules = """
Enfócate en modificar los campos relacionados a la Oferta Técnica:
- metadata (cliente, fecha, etc)
- TEXTO_MATERIALES_CLIENTE, TEXTO_MATERIALES_IMA
- TEXTO_PERFILES_PERSONAL, TEXTO_REQUISITOS_ADICIONALES
- TEXTO_HERRAMIENTAS_Y_EPP, TEXTO_SSMA
- TEXTO_TAREAS_DEFINIDAS, TEXTO_ENCUADRE_GREMIAL, etc.
"""
    elif chat_type == 'CONSULTAS':
        context_rules = """
Enfócate en modificar los campos relacionados a Consultas (RFI):
- consultas_generales (lista de dicts con 'seccion' y 'consulta')
- inconsistencias (lista de dicts con 'ubicacion' y 'descripcion')
Añade, modifica o elimina elementos de estas listas según pida el usuario.
"""

    prompt = PromptTemplate.from_template(
        """Eres un experto ingeniero de licitaciones de IMA Servicios Industriales.
Tu tarea es modificar el siguiente JSON (parsed_data) de la licitación, aplicando estrictamente la petición del usuario.

JSON ACTUAL:
{json_str}

HISTORIAL RECIENTE:
{history_str}

INSTRUCCIÓN DEL USUARIO:
{user_instruction}

REGLAS:
1. Identifica qué campo del JSON necesita cambiar y modifícalo.
2. {context_rules}
3. Devuelve ÚNICAMENTE el JSON completo modificado válido. Nada de texto explicativo, nada de markdown ````json```` alrededor. Solo llaves {{}}.
"""
    )
    
    prompt_value = prompt.format(
        json_str=json_str,
        history_str=history_str,
        user_instruction=user_instruction,
        context_rules=context_rules
    )
    
    from src.core.analyzer import invoke_with_retry
    response = invoke_with_retry(prompt_value)
    
    content = response.content
    if isinstance(content, list):
        texto_res = "".join(
            c.get("text", "") if isinstance(c, dict) else str(c)
            for c in content
        ).strip()
    else:
        texto_res = str(content).strip()
    # Remover posibles tags markdown
    if texto_res.startswith("```json"):
        texto_res = texto_res[7:]
    if texto_res.startswith("```"):
        texto_res = texto_res[3:]
    if texto_res.endswith("```"):
        texto_res = texto_res[:-3]
        
    try:
        # Extraer JSON de bloques markdown o texto circundante
        clean_text = texto_res
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0]
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0]
        else:
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1:
                clean_text = clean_text[start:end+1]

        clean_text = clean_text.strip()
        
        try:
            import json_repair
            updated_json = json_repair.loads(clean_text)
        except Exception:
            updated_json = json.loads(clean_text)

        if isinstance(updated_json, dict) and updated_json:
            # Hacer merge con el original para preservar campos no modificados
            merged = current_json.copy()
            merged.update(updated_json)

            # Sincronizar campos de texto hacia dynamic_content si existen
            if "dynamic_content" not in merged or not isinstance(merged["dynamic_content"], dict):
                merged["dynamic_content"] = {}
                
            ot_fields = [
                "TITULO_OBRA", "TEXTO_LUGAR_PRESTACION", "TEXTO_HORARIOS", "TEXTO_ALCANCE_GENERAL", 
                "TEXTO_TAREAS_DEFINIDAS", "TEXTO_MATERIALES_CLIENTE", "TEXTO_MATERIALES_IMA", 
                "TEXTO_PERFILES_PERSONAL", "TEXTO_REQUISITOS_ADICIONALES",
                "TEXTO_ENCUADRE_GREMIAL", "TEXTO_HERRAMIENTAS_Y_EPP", 
                "TEXTO_SSMA", "TEXTO_CONDICIONES_COMERCIALES", "TEXTO_COMUNICACION"
            ]
            for fld in ot_fields:
                if fld in updated_json:
                    merged["dynamic_content"][fld] = updated_json[fld]
                elif fld in merged:
                    merged["dynamic_content"][fld] = merged[fld]

            return merged
        return current_json
    except Exception as e:
        print(f"Error decodificando el JSON modificado: {e}")
        return current_json
