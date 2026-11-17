import os
import time
import re
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from tenacity import retry, wait_exponential, stop_after_attempt

# Cargar variables de entorno desde el archivo .env
load_dotenv(override=True)

def get_anthropic_api_key():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Falta configurar ANTHROPIC_API_KEY en tu archivo .env")
    return api_key

def invoke_with_retry(prompt_value):
    import time
    api_key = get_anthropic_api_key()
    max_intentos = 5
    
    for intento in range(max_intentos):
        try:
            print(f"  -> Intento {intento+1} enviando a Claude...")
            # Usar claude-sonnet-5 que es el válido en este entorno
            modelo = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
            print(f"  -> Utilizando modelo: {modelo}")
            llm = ChatAnthropic(model_name=modelo, anthropic_api_key=api_key, max_tokens=8192)
            return llm.invoke(prompt_value)
        except Exception as e:
            error_msg = str(e)
            print(f"  [!] Falló el intento {intento+1}: {error_msg}")
            
            if intento < max_intentos - 1:
                wait_time = 15 # Espera por defecto para errores de red o rate limits
                if 'rate_limit' in error_msg.lower() or '429' in error_msg:
                    wait_time = 20.0
                
                print(f"  -> Esperando {wait_time:.1f} segundos antes de reintentar...")
                time.sleep(wait_time)
            else:
                raise e


def _build_llm():

    from langchain_anthropic import ChatAnthropic
    api_key = get_anthropic_api_key()
    import os
    from dotenv import load_dotenv
    load_dotenv()
    modelo = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    return ChatAnthropic(
        model_name=modelo, 
        anthropic_api_key=api_key, 
        max_tokens=8192
    )

def _invoke_llm(llm, prompt_value):
    from tenacity import retry, stop_after_attempt, wait_exponential
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _do_invoke():
        response = llm.invoke(prompt_value)
        content = response.content
        if isinstance(content, list):
            content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
        elif not isinstance(content, str):
            content = str(content)
        
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
            
        json_str = json_str.strip()
        import json_repair
        return json_repair.loads(json_str)
    try:
        return _do_invoke()
    except Exception as e:
        print(f"  [!] Falló el intento: {str(e)}")
        raise e

def _analyze_chunk(task_name, template, combined_text):

    llm = _build_llm()
    prompt = PromptTemplate.from_template(template)
    
    # Dividir combined_text en fragmentos más pequeños para no exceder los tokens de salida
    chunk_size = 40000
    chunks = [combined_text[i:i+chunk_size] for i in range(0, len(combined_text), chunk_size)]
    
    print(f"  -> Ejecutando análisis: {task_name} (dividido en {len(chunks)} fragmentos)...")
    
    merged_json = {}
    
    for idx, text_chunk in enumerate(chunks):
        print(f"     Procesando fragmento {idx+1}/{len(chunks)} para {task_name}...")
        prompt_value = prompt.invoke({"text": text_chunk})
        try:
            res = _invoke_llm(llm, prompt_value)
            # Mezclar el resultado en merged_json
            if isinstance(res, dict):
                for key, value in res.items():
                    if key not in merged_json:
                        merged_json[key] = value
                    else:
                        if isinstance(merged_json[key], list) and isinstance(value, list):
                            merged_json[key].extend(value)
                        elif isinstance(merged_json[key], dict) and isinstance(value, dict):
                            for sub_key, sub_val in value.items():
                                if sub_key not in merged_json[key]:
                                    merged_json[key][sub_key] = sub_val
                                else:
                                    if isinstance(merged_json[key][sub_key], list) and isinstance(sub_val, list):
                                        merged_json[key][sub_key].extend(sub_val)
                                    # Si es string, mantenemos el primero o concatenamos (mejor mantener el del primer chunk para metadatos)
        except Exception as e:
            print(f"  [x] Error en fragmento {idx+1} de {task_name}: {e}")
            
    print(f"  -> Completado análisis: {task_name} exitosamente.")
    return merged_json

def analyze_full_tender(docs):

    import re
    import concurrent.futures
    import json
    try:
        get_anthropic_api_key() 
    except Exception as e:
        return f"**Error de configuración:** {e}"

    if not docs:
        return "No hay documentos para analizar."

    print("Iniciando Pre-Filtrado Inteligente de texto...")
    
    keywords = [
        "plazo", "día", "dias", "meses", "fecha", "penalidad", "multa", "monto", 
        "presupuesto", "requisito", "obligatorio", "garantía", "garantia", "pago", 
        "entrega", "contrato", "vencimiento", "prórroga", "cláusula", "sanción", 
        "incumplimiento", "exigencia", "técnico", "especificación", "validez", 
        "condición", "oferta", "incongruencia", "contradicción", "$", "usd", "pesos",
        "agua", "luz", "energía", "residuo", "obrador", "logística", "proveer", 
        "cargo del", "sindicato", "gremio", "uocra", "convenio", "personal", "seguro", 
        "póliza", "notificación", "licitación", "licitacion", "concurso", "expediente",
        "alcance", "objeto", "lugar", "ubicación", "visita", "riesgo", "penalización"
    ]

    docs_by_source = {}
    max_chars = 35000

    for doc in docs:
        source = doc.metadata.get("source", "Desconocido") if hasattr(doc, 'metadata') else "Desconocido"
        if source not in docs_by_source:
            docs_by_source[source] = {'combined': "", 'first_done': False, 'done': False}
            
        state = docs_by_source[source]
        if state['done']:
            continue
            
        texto = doc.page_content if hasattr(doc, 'page_content') else str(doc)
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        if not texto:
            continue
            
        if not state['first_done']:
            if len(state['combined']) + len(texto) > max_chars:
                state['done'] = True
            else:
                state['combined'] += texto + "\n[PORTADA] "
            state['first_done'] = True
        else:
            texto_lower = texto.lower()
            if any(kw in texto_lower for kw in keywords):
                if len(state['combined']) + len(texto) > max_chars:
                    state['done'] = True
                else:
                    state['combined'] += texto + "\n[...] "

    filtered_docs = []
    for source, state in docs_by_source.items():
        if state['combined'].strip():
            filtered_docs.append(f"--- DOCUMENTO: {source} ---\n{state['combined']}\n")

    combined_text = "\n".join(filtered_docs)
    
    if not combined_text.strip():
        return "No se encontró información relevante o los archivos estaban vacíos."

    print("Enviando el pliego a la IA dividiendo la carga en 3 peticiones paralelas...")

    template_metadata_tecnicos = """
    Eres un experto Gerente Técnico y Operativo auditando un pliego de licitación.
    Tu objetivo es ser EXHAUSTIVO. No te limites, extrae toda la información posible.
    
    FORMATO DE SALIDA OBLIGATORIO (JSON Estricto):
    Debes devolver ÚNICAMENTE un objeto JSON válido. NO uses bloques de código, devuelve sólo el JSON crudo.
    Estructura esperada:
    {{"metadata":{{"nombre_pliego":"Nombre oficial","cliente":"Empresa","proceso":"Nro","moneda":"Moneda","planta":"Ubicación","requirente":"Req","comprador":"Comp","lista_documentos":"docs"}},"tecnicos":{{"alcance_general":"Resumen exhaustivo","ubicacion_obra":"Planta/lugar","horarios_exigidos":"L a V, etc","normas_ssma":["Cumplimiento 1","etc..."]}}}}
    Textos Extraídos:
    {text}
    """

    template_legales_inconsistencias = """
    Eres un Gerente General y Especialista en Licitaciones analizando un pliego.
    Tu objetivo es enfocarte en lo CRÍTICO. Extrae las penalidades, vacíos e inconsistencias 
    que sean REALMENTE IMPORTANTES y SIGNIFICATIVAS (ej. aquellas que impacten los costos, 
    la viabilidad operativa, o la seguridad). Evita extraer detalles menores o triviales.
    
    FORMATO DE SALIDA OBLIGATORIO (JSON Estricto):
    Debes devolver ÚNICAMENTE un objeto JSON válido. NO uses bloques de código, devuelve sólo el JSON crudo.
    Estructura esperada:
    {{"inconsistencias":[{{"documentos_conflicto":["Anexo 1","Pliego General"],"pagina_origen":"páginas...","cita_textual":"texto extraido completo...","descripcion_pregunta":"Explicación muy detallada","tipo":"Contradicción"}}], "legales":{{"penalidades_multas":["detalle de multa 1","etc..."],"vicios_o_vacios":["vacío contractual 1","etc..."],"condiciones_comerciales":["plazos","etc..."]}}}}
    Textos Extraídos:
    {text}
    """

    template_costos_consultas = """
    Eres un Gerente General y Experto en Licitaciones analizando un pliego.
    Extrae las variables de costo y formula consultas generales (técnicas, operativas, económicas) 
    que sean REALMENTE SIGNIFICATIVAS Y DE ALTO IMPACTO. Filtra y formula solo las consultas 
    que afecten directamente los costos de la operación, la seguridad o la viabilidad del proyecto. 
    Evita consultas triviales o menores.
    
    FORMATO DE SALIDA OBLIGATORIO (JSON Estricto):
    Debes devolver ÚNICAMENTE un objeto JSON válido. NO uses bloques de código, devuelve sólo el JSON crudo.
    Estructura esperada:
    {{"consultas_generales":[{{"categoria":"Operativa","archivo_origen":"doc","pagina_origen":"15","cita_textual":"cita exhaustiva","consulta":"Pregunta técnica exhaustiva"}}], "costos":{{"encuadre_gremial":"gremio aplicable","plazo_contrato_meses":12,"mano_de_obra":[{{"rol":"Rol exhaustivo","cantidad":"X","horas_mensuales":"Y","observaciones":"obs detallada"}}],"suministro_materiales":[{{"item":"item detallado","cantidad":"X","unidad":"U","observaciones":"obs"}}],"suministro_insumos":[],"subcontrataciones":[],"amortizacion_vehiculos":[],"equipos_menores":[],"instrucciones_especiales_cotizacion":["instr 1","instr 2"]}}}}
    Textos Extraídos:
    {text}
    """

    final_json = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_meta = executor.submit(_analyze_chunk, "Metadata_Tecnicos", template_metadata_tecnicos, combined_text)
        future_legales = executor.submit(_analyze_chunk, "Legales_Inconsistencias", template_legales_inconsistencias, combined_text)
        future_costos = executor.submit(_analyze_chunk, "Costos_Consultas", template_costos_consultas, combined_text)
        
        res_meta = future_meta.result()
        res_legales = future_legales.result()
        res_costos = future_costos.result()

    if res_meta: final_json.update(res_meta)
    if res_legales: final_json.update(res_legales)
    if res_costos: final_json.update(res_costos)

    return final_json


def create_vector_store(docs, persist_directory=None):
    import time
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    print("Inicializando modelo local de Embeddings (HuggingFace)... Esto puede tardar unos segundos la primera vez.")
    # Reducimos batch_size drásticamente para evitar OOM (Error 128) en la nube
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2", 
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'batch_size': 16}
    )
    
    print(f"Generando vectores localmente para {len(docs)} fragmentos...")
    start_time = time.time()
    
    # Inicializar Chroma vacío con soporte de persistencia si se provee directorio
    if persist_directory:
        vectorstore = Chroma(embedding_function=embeddings, persist_directory=persist_directory)
    else:
        vectorstore = Chroma(embedding_function=embeddings)
    
    # Procesar e insertar en lotes para mostrar una barra de progreso en consola
    batch_size = 500
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        vectorstore.add_documents(documents=batch)
        print(f"  -> Procesados {min(i+batch_size, len(docs))} de {len(docs)} fragmentos...")
        
    elapsed_time = time.time() - start_time
    print(f"Vectores generados exitosamente en {elapsed_time:.1f} segundos.")
        
    return vectorstore

def query_qa_bot(vectorstore, question):
    docs = vectorstore.similarity_search(question, k=5)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    prompt_template = """
    Eres un asistente experto en auditoría de licitaciones. Responde la siguiente pregunta de forma precisa y técnica usando EXCLUSIVAMENTE el contexto proporcionado.
    Al final de tu respuesta, menciona brevemente en qué páginas o documentos encontraste la información basándote en los marcadores [Página X] del contexto.
    Si la respuesta no está en el contexto, di "No encontré esta información en el pliego".
    
    Contexto recuperado:
    {context}
    
    Pregunta: {question}
    """
    
    prompt = PromptTemplate.from_template(prompt_template)
    prompt_value = prompt.invoke({"context": context, "question": question})
    
    response = invoke_with_retry(prompt_value)
    if isinstance(response.content, list):
        return "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in response.content])
    return str(response.content)
