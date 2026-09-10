class QueryGenerator:
    """
    Generador de Consultas (RFI - Request for Information).
    Toma el contexto de la licitación (documentos analizados, incongruencias detectadas)
    y formatea un documento profesional (Word/PDF) con las preguntas definitivas para el cliente.
    """
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        

    def generate_docx_from_json(self, parsed_data: dict, template_path: str, output_path: str) -> str:
        """
        Genera el documento de consultas formales inyectando los datos JSON en la plantilla Word.
        """
        import docx
        import os
        
        if not os.path.exists(template_path):
            return "Error: Plantilla de Consultas no encontrada."
            
        doc = docx.Document(template_path)
        
        # Reemplazo total de variables en los párrafos usando metadata del LLM
        metadata = parsed_data.get("metadata", {})
        lista_docs = str(metadata.get("lista_documentos", "No especificado en pliego"))
        lista_docs = ", ".join([doc.strip() for doc in lista_docs.split(",") if doc.strip()])
        
        variables_reemplazo = {
            "{{NOMBREPLIEGO}}": str(metadata.get("nombre_pliego", "No especificado en pliego")),
            "{{CLIENTE}}": str(metadata.get("cliente", "No especificado en pliego")),
            "{{PROCESO}}": str(metadata.get("proceso", "No especificado en pliego")),
            "{{MONEDA}}": str(metadata.get("moneda", "No especificado en pliego")),
            "{{PLANTA}}": str(metadata.get("planta", "No especificado en pliego")),
            "{{REQUIRENTE}}": str(metadata.get("requirente", "No especificado en pliego")),
            "{{COMPRADOR}}": str(metadata.get("comprador", "No especificado en pliego")),
            "{{LISTA_DOCUMENTOS}}": lista_docs
        }
        
        for p in doc.paragraphs:
            full_text = p.text
            if any(key in full_text for key in variables_reemplazo.keys()):
                # Realizar reemplazos en el texto completo
                for key, val in variables_reemplazo.items():
                    full_text = full_text.replace(key, val)
                
                # Solución a Run Splitting (Opción B):
                # Asignamos el texto reconstruido al primer run para mantener su estilo base,
                # y vaciamos el resto de los runs para evitar duplicados.
                if p.runs:
                    p.runs[0].text = full_text
                    for run in p.runs[1:]:
                        run.text = ""
        
        # Identificar las tablas dinámicamente y vaciar las filas viejas (manteniendo el encabezado)
        tabla_consultas = None
        tabla_inconsistencias = None
        
        for table in doc.tables:
            if not table.rows:
                continue
            headers = [cell.text.lower().strip() for cell in table.rows[0].cells]
            
            if "categoría" in headers or "categoria" in headers:
                tabla_consultas = table
            elif "tipo" in headers or "documentos en conflicto" in headers:
                tabla_inconsistencias = table

        # Función auxiliar para limpiar la tabla dejando solo el encabezado
        def clear_table(table):
            # Iteramos en reversa para no afectar el índice mientras borramos (XML level)
            for row in table.rows[1:][::-1]:
                tbl = table._tbl
                tr = row._tr
                tbl.remove(tr)

        # Contador global para numeración continua de filas en ambas tablas
        contador_global = 1

        # Llenar Tabla de Consultas Generales
        if tabla_consultas and "consultas_generales" in parsed_data:
            clear_table(tabla_consultas)
            consultas = parsed_data["consultas_generales"]
            
            for c in consultas:
                row_cells = tabla_consultas.add_row().cells
                if len(row_cells) >= 4:
                    row_cells[0].text = str(contador_global)
                    row_cells[1].text = str(c.get("categoria", ""))
                    row_cells[2].text = f"{c.get('archivo_origen', '')}\nPág: {c.get('pagina_origen', 'N/A')}\n\"{c.get('cita_textual', 'N/A')}\""
                    row_cells[3].text = str(c.get("consulta", ""))
                    contador_global += 1

        # Llenar Tabla de Inconsistencias
        if tabla_inconsistencias and "inconsistencias" in parsed_data:
            clear_table(tabla_inconsistencias)
            incons = parsed_data["inconsistencias"]
            
            for i in incons:
                row_cells = tabla_inconsistencias.add_row().cells
                if len(row_cells) >= 4:
                    row_cells[0].text = str(contador_global)
                    row_cells[1].text = str(i.get("tipo", "Inconsistencia"))
                    
                    # Formateo correcto: si es lista, unir con comas
                    docs_conflicto = i.get("documentos_conflicto", "")
                    if isinstance(docs_conflicto, list):
                        docs_conflicto = ", ".join(docs_conflicto)
                    row_cells[2].text = f"{docs_conflicto}\nPág: {i.get('pagina_origen', 'N/A')}\n\"{i.get('cita_textual', 'N/A')}\""
                    
                    row_cells[3].text = str(i.get("descripcion_pregunta", ""))
                    contador_global += 1
                    
        # Al hacer save a 'output_path', mantenemos intacta la plantilla original.
        doc.save(output_path)
        return output_path
