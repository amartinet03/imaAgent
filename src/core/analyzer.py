import os
import time
import re
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
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
            # Recomendamos claude-sonnet-5
            modelo = "claude-sonnet-5" 
            print(f"  -> Utilizando modelo: {modelo}")
            llm = ChatAnthropic(model_name=modelo, anthropic_api_key=api_key)
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

def extract_relevant_paragraphs(chunks):
    """
    Filtro Inteligente V3: Comprime espacios y reduce a 150k caracteres 
    para garantizar absolutamente no tocar el techo de 250k tokens.
    """
    import re
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
    
    first_chunks = []
    keyword_chunks = []
    seen_sources = set()
    
    # 1. Separar portadas y párrafos clave
    for chunk in chunks:
        texto = chunk.page_content if hasattr(chunk, 'page_content') else str(chunk)
        # Comprimir todos los múltiples espacios/saltos de línea a uno solo (ahorra miles de tokens inútiles de Excel)
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        source = chunk.metadata.get("source", "Desconocido") if hasattr(chunk, 'metadata') else "Desconocido"
        
        if source not in seen_sources:
            seen_sources.add(source)
            first_chunks.append(texto)
        else:
            chunk_lower = texto.lower()
            if any(kw in chunk_lower for kw in keywords):
                keyword_chunks.append(texto)
            
    # 2. Ensamblar garantizando primero las portadas (metadata)
    combined = ""
    max_chars = 150000
    
    for text in first_chunks:
        if len(combined) + len(text) > max_chars:
            break
        combined += text + "\n[PORTADA] "
        
    # 3. Rellenar con contexto clave hasta el límite
    for text in keyword_chunks:
        if len(combined) + len(text) > max_chars:
            break
        combined += text + "\n[...] "
        
    return combined

def analyze_full_tender(docs):
    """
    Ejecuta un análisis instantáneo con Pre-Filtrado Heurístico (Mega-Prompt Unificado).
    """
    try:
        get_anthropic_api_key() # Verificar configuración
    except Exception as e:
        return f"**Error de configuración:** {e}"

    if not docs:
        return "No hay documentos para analizar."

    # --- AGRUPAR CHUNKS POR DOCUMENTO ---
    docs_by_source = {}
    for doc in docs:
        source = doc.metadata.get("source", "Desconocido")
        if source not in docs_by_source:
            docs_by_source[source] = []
        docs_by_source[source].append(doc.page_content)

    print("Iniciando Pre-Filtrado Inteligente de texto para velocidad extrema...")
    filtered_docs = []
    
    for source, chunks in docs_by_source.items():
        # Pasar directamente la lista de chunks para mantener el contexto
        filtered_text = extract_relevant_paragraphs(chunks)
        
        # Solo incluir si quedó algo después del filtrado
        if filtered_text.strip():
            filtered_docs.append(f"--- DOCUMENTO: {source} ---\n{filtered_text}\n")

    combined_text = "\n".join(filtered_docs)
    
    if not combined_text.strip():
        return "No se encontró información relevante o los archivos estaban vacíos."

    print("Enviando todo el pliego a la IA en 1 sola petición...")

    # --- ÚNICA FASE DE ANÁLISIS EXHAUSTIVO (MEGA-PROMPT) ---
    analysis_template = """
    Eres un equipo multidisciplinario experto compuesto por:
    1. Un Abogado Senior (Legales y Riesgos): Analiza minuciosamente cláusulas, penalidades, multas abusivas, contradicciones, SLA y vacíos contractuales.
    2. Un Estimador Líder (Cotizador): Extrae variables duras de costo: cantidad y tipos de mano de obra (turnos, convenios), vehículos exigidos, herramientas, EPP especiales, seguros específicos.
    3. Un Gerente Técnico (Operaciones): Define el alcance general, horarios, ubicación, normas SSMA/HSE.
    4. Un Ingeniero Experto en Auditoría de Pliegos: Genera consultas técnicas y comerciales formales (RFI) sobre vacíos en provisiones o procedimientos.

    REGLAS ESTRICTAS DE EXTRACCIÓN:
    - TIENES EL PLIEGO COMPLETO. Tu objetivo es encontrar todas las anomalías y detalles posibles.
    - NO alucines. Si un dato no está en el texto, coloca `null` o una lista vacía `[]`.
    - Sé extremadamente detallista. NO RESUMAS los hallazgos críticos.
    - Debes generar AL MENOS 10 consultas (RFIs) y 5 inconsistencias, revisando cada anexo, norma y cláusula que parezca abusiva o incompleta.
    - El campo "categoria" en "consultas_generales" SOLO puede contener: "Operativa", "Técnica", o "Económica".
    - Agrupa todos los documentos faltantes en una sola consulta.

    FORMATO DE SALIDA OBLIGATORIO (JSON Estricto):
    Debes devolver ÚNICAMENTE un objeto JSON válido, sin texto adicional antes o después. 
    Estructura esperada:
    {{
        "metadata": {{
            "nombre_pliego": "[Nombre oficial o título principal del pliego/licitación]",
            "cliente": "[Nombre real de la empresa contratante]",
            "proceso": "[Nombre o número real de la licitación/proceso]",
            "moneda": "[Moneda solicitada para cotizar, ej: Pesos argentinos o USD]",
            "planta": "[Lugar físico o planta real de la obra]",
            "requirente": "[Nombre de la persona o sector que solicita, si figura]",
            "comprador": "[Nombre del comprador de compras, si figura]",
            "lista_documentos": "[Lista de todos los documentos y anexos provistos y analizados, separados por comas]"
        }},
        "legales": {{
            "contradicciones": ["contradicción 1", "contradicción 2"],
            "penalidades_multas": ["detalle de multa 1"],
            "vicios_o_vacios": ["vacío 1"],
            "consultas_rfi": ["pregunta formal a enviar a Compras 1", "pregunta 2"],
            "condiciones_comerciales": ["plazo de pago a 60 días", "certificación mensual", "ajuste de tarifas"]
        }},
        "costos": {{
            "encuadre_gremial": "UOCRA, UOM, Petroleros u otro mencionado en el pliego",
            "mano_de_obra": [
                {{"rol": "oficial especializado", "cantidad": "2", "turno": "diurno", "observaciones": "comentarios"}}
            ],
            "insumos_y_epp": [
                {{"insumo": "EPP ignífugo", "unidad": "global", "cantidad": "1", "costo_ref": ""}}
            ],
            "vehiculos_y_equipos": [
                {{"vehiculo": "camioneta", "cantidad": "1", "dedicacion": "mensual", "observaciones": ""}}
            ],
            "seguros_y_garantias": [
                {{"tipo": "seguro responsabilidad civil 1M", "cobertura": "1M", "observaciones": ""}}
            ],
            "instrucciones_especiales_cotizacion": ["nota: tener en cuenta costo financiero a 60 días"]
        }},
        "tecnicos": {{
            "alcance_general": "Resumen del objetivo del servicio",
            "ubicacion_obra": "Planta X",
            "horarios_exigidos": "L a V de 7 a 16hs",
            "normas_ssma": ["Cumplimiento reglas de oro", "Proceso Greenbanding"]
        }},
        "consultas_generales": [
            {{
                "categoria": "Operativa",
                "archivo_origen": "Pliego_Condiciones.pdf",
                "pagina_origen": "15",
                "cita_textual": "texto extraido...",
                "consulta": "Pregunta detallada sobre vacío detectado"
            }}
        ],
        "inconsistencias": [
            {{
                "tipo": "Contradicción",
                "documentos_conflicto": ["Anexo 1", "Pliego General"],
                "pagina_origen": "5 y 12",
                "cita_textual": "texto en conflicto...",
                "descripcion_pregunta": "Explicación del problema"
            }}
        ]
    }}

    Textos Extraídos:
    {text}
    """
    
    analysis_prompt = PromptTemplate.from_template(analysis_template)
    
    try:
        prompt_value = analysis_prompt.invoke({"text": combined_text})
        response = invoke_with_retry(prompt_value)
        
        # Intentar extraer el JSON de la respuesta
        content = response.content
        import json
        import re
        
        if isinstance(content, list):
            content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
        elif not isinstance(content, str):
            content = str(content)
            
        # Limpiar markdown de json si existe
        match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', content, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = content
            
        try:
            parsed_data = json.loads(json_str)
            return parsed_data
        except json.JSONDecodeError:
            # Fallback en caso de que el modelo haya devuelto texto
            print("No se pudo parsear como JSON, devolviendo crudo.")
            return {"error": "Formato inválido", "raw": content}
            
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'last_attempt') and e.last_attempt is not None:
            real_e = e.last_attempt.exception()
            if real_e:
                error_msg = str(real_e)
        return f"Ocurrió un error en el análisis instantáneo de Google: {error_msg}\n\nAsegúrate de no exceder los límites de tu plan."

def create_vector_store(docs, persist_directory=None):
    import time
    print("Inicializando modelo local de Embeddings (HuggingFace)... Esto puede tardar unos segundos la primera vez.")
    # Aumentamos el batch_size de HuggingFace para usar mejor la CPU
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", encode_kwargs={'batch_size': 128})
    
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
