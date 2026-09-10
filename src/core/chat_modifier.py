import json
import re
from langchain_core.prompts import PromptTemplate
from src.core.analyzer import invoke_with_retry

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
        updated_json = json.loads(texto_res.strip())
        return updated_json
    except json.JSONDecodeError as e:
        print(f"Error decodificando el JSON modificado: {e}")
        # Retornamos el original si falla para no romper nada
        return current_json
