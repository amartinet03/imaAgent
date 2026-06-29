import os
import time
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from tenacity import retry, wait_exponential, stop_after_attempt
import re

# Cargar variables de entorno desde el archivo .env
# Forzamos override=True para que siempre lea la última versión del archivo, incluso si se modificó con la app corriendo.
load_dotenv(override=True)

def get_llm():
    # Volvemos a Google Gemini porque el nivel gratuito de Groq solo permite 12,000 tokens por minuto
    # y el pliego filtrado tiene 50,962 tokens. Gemini nos da 250,000 tokens por minuto.
    # Usaremos gemini-2.5-flash que comprobé que funciona y tiene alta cuota.
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("Falta configurar GOOGLE_API_KEY. Configúrala en tu entorno o en un archivo .env")
    
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

def invoke_with_retry(llm, prompt_value):
    # Bucle de reintento manual que detecta el error 429 (Resource Exhausted)
    import time
    import re
    max_intentos = 5
    for intento in range(max_intentos):
        try:
            print(f"  -> Intento {intento+1} enviando a la IA...")
            return llm.invoke(prompt_value)
        except Exception as e:
            error_msg = str(e)
            print(f"  [!] Falló el intento {intento+1}: {error_msg}")
            
            if intento < max_intentos - 1:
                wait_time = 15 # Espera por defecto para otros errores
                
                if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg:
                    # Intentar extraer el tiempo que sugiere Google (ej: "retry in 37.04s")
                    match = re.search(r'retry in ([\d\.]+)s', error_msg)
                    if match:
                        wait_time = float(match.group(1)) + 2.0 # Margen de seguridad
                    else:
                        wait_time = 45 # Si no encontramos los segundos, esperamos 45s por seguridad
                
                print(f"  -> Cuota excedida o error. Esperando {wait_time:.1f} segundos antes de reintentar...")
                time.sleep(wait_time)
            else:
                raise e

def extract_relevant_paragraphs(chunks):
    """
    Filtra usando los 'chunks' completos generados por LangChain.
    Como los chunks tienen un overlap (superposición), nunca se corta una frase a la mitad,
    incluso si el PDF tenía saltos de línea extraños.
    """
    keywords = [
        "plazo", "día", "dias", "meses", "fecha", "penalidad", "multa", 
        "monto", "presupuesto", "requisito", "obligatorio", "garantía", "garantia",
        "pago", "entrega", "entregar", "contrato", "vencimiento", "prórroga", 
        "prorroga", "cláusula", "sanción", "sancion", "incumplimiento", 
        "exigencia", "técnico", "tecnico", "especificación", "especificacion", 
        "validez", "condición", "condicion", "oferta", "incongruencia", "contradicción",
        "$", "usd", "pesos",
        # Nuevas palabras operativas, gremiales y de riesgo administrativo
        "agua", "luz", "energía", "energia", "residuo", "obrador", "logística", "logistica",
        "proveer", "proveerá", "proveera", "cargo del", "sindicato", "gremio", "uocra",
        "convenio", "personal", "seguro", "póliza", "poliza", "notificación"
    ]
    
    relevant_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        if any(kw in chunk_lower for kw in keywords):
            relevant_chunks.append(chunk.strip())
            
    # Unir los bloques relevantes
    return "\n\n[...] ".join(relevant_chunks)

def analyze_cross_document_conflicts(docs):
    """
    Ejecuta un análisis instantáneo con Pre-Filtrado Heurístico.
    """
    try:
        llm = get_llm()
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
    
    # Límite máximo de seguridad para la cuota gratuita (aprox 800,000 caracteres = ~200k tokens)
    if len(combined_text) > 800000:
        combined_text = combined_text[:800000] + "\n[...Texto truncado para cumplir cuota gratuita de 250k tokens...]"

    if not combined_text.strip():
        return "No se encontró información relevante sobre plazos, montos o penalidades en los documentos, o los archivos estaban vacíos."

    print("Texto pre-filtrado completado. Enviando todo el pliego a la IA en 1 sola petición...")

    # --- ÚNICA FASE DE ANÁLISIS ---
    analysis_template = """
    Rol y Objetivo:
    Eres un Consultor Senior en Administración de Contratos, Legales y Gestión de Obra con 20 años de experiencia en el sector industrial. Tu capacidad crítica es infalible. Tu objetivo es auditar el paquete documental adjunto para detectar riesgos comerciales, sobrecostos, paralizaciones de obra, incongruencias contractuales graves y vacíos legales reales.

    Metodología de Razonamiento y Filtros (¡IMPORTANTE!):
    Antes de redactar el reporte, realiza un análisis interno siguiendo este orden riguroso en la sección <razonamiento>:

    1. Filtro de Jerarquía (Lex specialis): Los documentos particulares (Carta Oferta, Legajo Técnico) prevalecen sobre los genéricos (Condiciones Generales). Si un documento particular contradice al general, NO es una contradicción, sino que prevalece el particular (pero debes señalarlo como prevalencia).
    2. Regla de la Excepción: Si una cláusula da una regla general ("pagos a 30 días") y otra da una regla específica ("pagos en moneda extranjera a 15 días"), ESTO NO ES UNA CONTRADICCIÓN. Es una excepción válida.
    3. Filtro Operativo y Logístico: Analiza si el pliego impone cargas logísticas no remuneradas (ej. provisión de agua/luz, gestión de residuos, obradores). ¿Es claro quién paga por esto? No ignores la parte operativa.
    4. Filtro Laboral/Sindical: Identifica menciones a convenios colectivos (ej. UOCRA regional, sindicatos específicos). ¿Qué riesgo de paralización implica esto si no estamos alineados?
    5. Filtro de Riesgo Administrativo: Busca plazos de notificación, multas y trámites de seguros. ¿Los plazos son realistas para la operación diaria de una obra?
    6. Conocimiento Operativo Industrial: No mezcles conceptos. Un "Permiso de Trabajo" (PT) autoriza una tarea en el tiempo; un "Certificado" (ej. espacio confinado, anulación de alarmas) es un anexo de corta duración. La habilitación de una persona (carnet) tiene plazos distintos a la inspección de un equipo (oblea/código de colores). Analiza cada uno por separado.
    7. Sentido Común Contractual: Ignora variables como "0", "NaN" o campos vacíos en plantillas de Excel. Es evidente que son formularios a completar por el oferente.
    8. Prohibido alucinar: Si un dato (ej. fecha de póliza, monto de multa) no está explícitamente en el texto, escribe "Información no disponible". No inventes fechas ni documentos.

    Instrucción de Ejecución:
    Abre un bloque <razonamiento> para analizar todo usando los filtros anteriores. Si una supuesta "contradicción" es en realidad una excepción o una plantilla en blanco, descártala. Luego de razonar, redacta el siguiente formato:

    Formato de Salida Requerido:

    ⚠️ Incongruencias Críticas: Contradicciones reales directas entre documentos. Cita textualmente el Documento y la Cláusula de donde lo sacas.

    ⚙️ Riesgos Operativos y Logísticos: Falta de claridad en quién provee qué, cargas de gestión imprevistas, hitos técnicos mal definidos.

    📢 Alerta Gremial/Laboral y Administrativa: Riesgo de bloqueo sindical por convenios, o plazos de notificación de multas irreales.

    ❓ Ambigüedades Legales: Errores de redacción del cliente que ponen en riesgo la cotización (ej. porcentajes erróneos o topes incongruentes).

    📝 Consultas Sugeridas (RFI): Redacta 3 o 4 preguntas formales, directas y profesionales listas para enviar a Compras para aclarar estos problemas antes de cotizar.

    Textos Extraídos:
    {text}
    """
    
    analysis_prompt = PromptTemplate.from_template(analysis_template)
    
    try:
        prompt_value = analysis_prompt.invoke({"text": combined_text})
        response = invoke_with_retry(llm, prompt_value)
        return response.content
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'last_attempt') and e.last_attempt is not None:
            real_e = e.last_attempt.exception()
            if real_e:
                error_msg = str(real_e)
        return f"Ocurrió un error en el análisis instantáneo de Google: {error_msg}\n\nAsegúrate de no exceder los límites de tu plan."
