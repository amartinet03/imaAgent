import json
import re

def modify_json_with_chat(current_json: dict, chat_history: list, user_instruction: str, chat_type: str = 'OT') -> dict:
    """
    Modifica el JSON de parsed_data basándose en la instrucción del usuario.
    Especializado y optimizado por tipo de chat para garantizar respuestas rápidas,
    precisas y sin truncamiento de tokens.
    """
    history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history[-5:]])

    if chat_type == 'CONSULTAS':
        # 1. Preparar listas numeradas continuas para que el usuario pueda referenciar por N° (ej. "elimina la consulta 14")
        raw_consultas = current_json.get("consultas_generales") or []
        raw_inconsistencias = current_json.get("inconsistencias") or []

        idx = 1
        numbered_consultas = []
        for c in raw_consultas:
            item = dict(c)
            item["numero"] = idx
            numbered_consultas.append(item)
            idx += 1

        numbered_inconsistencias = []
        for inc in raw_inconsistencias:
            item = dict(inc)
            item["numero"] = idx
            numbered_inconsistencias.append(item)
            idx += 1

        input_payload = {
            "consultas_generales": numbered_consultas,
            "inconsistencias": numbered_inconsistencias
        }
        json_str = json.dumps(input_payload, ensure_ascii=False, indent=2)

        prompt_text = f"""Eres un ingeniero experto en licitaciones de IMA Servicios Industriales.
Tu tarea es modificar la lista de Consultas (RFI) e Inconsistencias aplicando ESTRICTAMENTE la instrucción del usuario.

LISTADO ACTUAL DE CONSULTAS E INCONSISTENCIAS:
{json_str}

HISTORIAL RECIENTE:
{history_str}

INSTRUCCIÓN DEL USUARIO:
{user_instruction}

REGLAS ESPECÍFICAS:
1. Si el usuario pide AGREGAR una consulta o pregunta:
   Agrega un nuevo objeto a "consultas_generales" con la siguiente estructura exacta:
   {{"categoria": "Técnica / Comercial / Equipos", "archivo_origen": "Pliego General", "pagina_origen": "N/A", "cita_textual": "Tema relacionado", "consulta": "La pregunta redactada de forma profesional"}}
2. Si el usuario pide ELIMINAR una consulta o inconsistencia (por número ej. 'elimina la consulta 14' o por tema):
   Identifica el objeto correspondiente por su campo 'numero' o su texto y remuévelo del listado.
3. Si el usuario pide MODIFICAR o REESCRIBIR:
   Modifica el texto de la consulta o inconsistencia indicada.
4. Devuelve ÚNICAMENTE un objeto JSON válido con las dos claves: "consultas_generales" e "inconsistencias". No agregues texto introductorio ni explicaciones fuera del JSON.
"""

    else:
        # OT (Oferta Técnica)
        ot_fields = [
            "TITULO_OBRA", "TEXTO_LUGAR_PRESTACION", "TEXTO_HORARIOS", "TEXTO_ALCANCE_GENERAL", 
            "TEXTO_TAREAS_DEFINIDAS", "TEXTO_MATERIALES_CLIENTE", "TEXTO_MATERIALES_IMA", 
            "TEXTO_PERFILES_PERSONAL", "TEXTO_REQUISITOS_ADICIONALES",
            "TEXTO_ENCUADRE_GREMIAL", "TEXTO_HERRAMIENTAS_Y_EPP", 
            "TEXTO_SSMA", "TEXTO_CONDICIONES_COMERCIALES", "TEXTO_COMUNICACION"
        ]
        dynamic_content = current_json.get("dynamic_content") or {}
        ot_payload = {
            "metadata": current_json.get("metadata", {}),
            "secciones_ot": {}
        }
        for fld in ot_fields:
            ot_payload["secciones_ot"][fld] = current_json.get(fld) or dynamic_content.get(fld, "")

        json_str = json.dumps(ot_payload, ensure_ascii=False, indent=2)

        prompt_text = f"""Eres un ingeniero experto en licitaciones de IMA Servicios Industriales.
Tu tarea es modificar las secciones de la Oferta Técnica (OT) aplicando ESTRICTAMENTE la instrucción del usuario.

SECCIONES ACTUALES DE LA OFERTA TÉCNICA:
{json_str}

HISTORIAL RECIENTE:
{history_str}

INSTRUCCIÓN DEL USUARIO:
{user_instruction}

REGLAS ESPECÍFICAS:
1. Identifica qué sección o campo de "secciones_ot" necesita cambiar y modifícalo aplicando lo que pidió el usuario.
2. Mantén el estilo profesional, directo y en tercera persona ("IMA").
3. Devuelve ÚNICAMENTE un objeto JSON válido con los campos modificados de "secciones_ot" (o todas las "secciones_ot"). No agregues texto introductorio.
"""

    from src.core.analyzer import invoke_with_retry
    response = invoke_with_retry(prompt_text)
    
    content = response.content
    if isinstance(content, list):
        clean_text = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content).strip()
    else:
        clean_text = str(content).strip()

    # Limpiar bloques markdown
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
        updated_data = json_repair.loads(clean_text)
    except Exception:
        try:
            updated_data = json.loads(clean_text)
        except Exception as e_json:
            print(f"[Chat Modifier Error] No se pudo decodificar JSON: {e_json}\nTexto recibido: {clean_text[:200]}")
            return current_json

    if not isinstance(updated_data, dict):
        print(f"[Chat Modifier] Respuesta no es un dict: {clean_text[:100]}")
        return current_json

    result_json = current_json.copy()

    if chat_type == 'CONSULTAS':
        # Extraer listas actualizadas y limpiar campo 'numero'
        if "consultas_generales" in updated_data and isinstance(updated_data["consultas_generales"], list):
            clean_c = []
            for item in updated_data["consultas_generales"]:
                if isinstance(item, dict):
                    c_dict = dict(item)
                    c_dict.pop("numero", None)
                    clean_c.append(c_dict)
            result_json["consultas_generales"] = clean_c

        if "inconsistencias" in updated_data and isinstance(updated_data["inconsistencias"], list):
            clean_i = []
            for item in updated_data["inconsistencias"]:
                if isinstance(item, dict):
                    i_dict = dict(item)
                    i_dict.pop("numero", None)
                    clean_i.append(i_dict)
            result_json["inconsistencias"] = clean_i

    else:
        # OT
        ot_fields = [
            "TITULO_OBRA", "TEXTO_LUGAR_PRESTACION", "TEXTO_HORARIOS", "TEXTO_ALCANCE_GENERAL", 
            "TEXTO_TAREAS_DEFINIDAS", "TEXTO_MATERIALES_CLIENTE", "TEXTO_MATERIALES_IMA", 
            "TEXTO_PERFILES_PERSONAL", "TEXTO_REQUISITOS_ADICIONALES",
            "TEXTO_ENCUADRE_GREMIAL", "TEXTO_HERRAMIENTAS_Y_EPP", 
            "TEXTO_SSMA", "TEXTO_CONDICIONES_COMERCIALES", "TEXTO_COMUNICACION"
        ]
        sec_ot = updated_data.get("secciones_ot", updated_data)
        if "dynamic_content" not in result_json or not isinstance(result_json["dynamic_content"], dict):
            result_json["dynamic_content"] = {}

        if isinstance(sec_ot, dict):
            for k, v in sec_ot.items():
                if k in ot_fields:
                    result_json[k] = v
                    result_json["dynamic_content"][k] = v
        
        if "metadata" in updated_data and isinstance(updated_data["metadata"], dict):
            result_json["metadata"].update(updated_data["metadata"])

    print(f"[Chat Modifier] Modificación exitosa para {chat_type}.")
    return result_json
