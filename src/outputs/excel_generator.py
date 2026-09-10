class ExcelGenerator:
    """
    Generador del Excel de Costos.
    Extrae cantidades y requisitos mínimos (ej. dotación, vehículos, herramientas)
    del pliego y las circulares, volcándolos en un Excel preformateado para que 
    el equipo de precios aplique costos locales e impuestos.
    """
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
    def generate_cost_excel(self, tender_context: dict, template_path: str, output_path: str) -> str:
        """
        Genera un nuevo Excel de Costos para la licitación.
        Crea pestañas estandarizadas (Mano de Obra, Equipos, Insumos, Subcontrataciones)
        y pre-carga los requerimientos extraídos por la IA en las filas correspondientes,
        usando un formato de tabla limpio para que el equipo comercial lo cotice.
        """
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        parsed_data = tender_context.get("parsed_data", {})
        costos = parsed_data.get("costos", {})
        metadata = parsed_data.get("metadata", {})
        
        # Extraer listas (si están vacías, agregamos una fila genérica para no dejar vacío)
        mo_list = costos.get("mano_de_obra", []) or ["Completar mano de obra requerida"]
        epp_list = costos.get("insumos_y_epp", []) or ["Completar insumos/epp"]
        veh_list = costos.get("vehiculos_y_equipos", []) or ["Completar vehículos y equipos"]
        seg_list = costos.get("seguros_y_garantias", []) or ["Completar seguros requeridos"]
        
        # Helper to extract from list of dicts or strings
        def get_col(lst, key, is_string_fallback=False):
            res = []
            for item in lst:
                if isinstance(item, dict):
                    res.append(item.get(key, ""))
                else:
                    res.append(str(item) if is_string_fallback else "")
            return res
            
        # Armar los DataFrames con la estructura deseada
        # 1. Mano de Obra
        df_mo = pd.DataFrame({
            "Categoría / Rol": get_col(mo_list, "rol", True),
            "Cantidad Requerida": get_col(mo_list, "cantidad"),
            "Turno / Horas (HHN)": get_col(mo_list, "turno"),
            "Observaciones del Pliego": get_col(mo_list, "observaciones")
        })
        
        # 2. Equipos y Vehículos
        df_veh = pd.DataFrame({
            "Descripción del Equipo / Vehículo": get_col(veh_list, "vehiculo", True),
            "Cantidad": get_col(veh_list, "cantidad"),
            "Dedicación (Meses/Días)": get_col(veh_list, "dedicacion"),
            "Observaciones": get_col(veh_list, "observaciones")
        })
        
        # 3. Suministro de Insumos
        df_ins = pd.DataFrame({
            "Descripción del Insumo / EPP": get_col(epp_list, "insumo", True),
            "Unidad": get_col(epp_list, "unidad"),
            "Cantidad Estimada": get_col(epp_list, "cantidad"),
            "Costo Unit. Ref.": get_col(epp_list, "costo_ref")
        })
        
        # 4. Seguros y Garantías
        df_seg = pd.DataFrame({
            "Tipo de Seguro / Caución / Garantía": get_col(seg_list, "tipo", True),
            "Cobertura o Monto Exigido": get_col(seg_list, "cobertura"),
            "Observaciones": get_col(seg_list, "observaciones")
        })
        
        # 5. Resumen Ejecutivo (Portada)
        df_resumen = pd.DataFrame({
            "Parámetro": ["Cliente", "Proyecto / Licitación", "Encuadre Gremial", "Instrucciones Especiales"],
            "Valor": [
                metadata.get("cliente", "No especificado"),
                metadata.get("proceso", "No especificado"),
                costos.get("encuadre_gremial", "No especificado"),
                " | ".join(costos.get("instrucciones_especiales_cotizacion", []))
            ]
        })

        # Exportar a Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_resumen.to_excel(writer, sheet_name="0 RESUMEN", index=False)
            df_mo.to_excel(writer, sheet_name="1 MANO DE OBRA", index=False)
            df_veh.to_excel(writer, sheet_name="Equipos", index=False)
            df_ins.to_excel(writer, sheet_name="3 SUMINISTRO DE INSUMOS", index=False)
            df_seg.to_excel(writer, sheet_name="4 SEGUROS Y GARANTIAS", index=False)
            
        # Dar formato visual con openpyxl
        wb = openpyxl.load_workbook(output_path)
        
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            
            # Formato encabezados
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
                
            # Ajustar anchos y formato celdas
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                    if cell.row > 1:
                        cell.border = thin_border
                adjusted_width = (max_length + 2)
                if adjusted_width > 50: adjusted_width = 50
                ws.column_dimensions[column].width = adjusted_width
                
        wb.save(output_path)
        return output_path

    def validate_cost_excel(self, tender_context: dict, uploaded_excel_path: str) -> str:
        """
        Lee el Excel completado por el equipo y lo compara contra los requerimientos 
        extraídos del pliego para detectar incongruencias usando el LLM.
        """
        import openpyxl
        
        if not self.llm_client:
            raise ValueError("No LLM client configured for Excel validation")
            
        # Extraer requisitos
        parsed_data = tender_context.get("parsed_data", {})
        costos = parsed_data.get("costos", {})
        req_text = f"Mano de obra: {costos.get('mano_de_obra')}\nVehiculos: {costos.get('vehiculos_y_equipos')}\nInsumos: {costos.get('insumos_y_epp')}"
        
        # Extraer contenido del Excel
        wb = openpyxl.load_workbook(uploaded_excel_path, data_only=True)
        excel_dump = ""
        
        for sheet_name in ["1 MANO DE OBRA", "Equipos", "3 SUMINISTRO DE INSUMOS", "Presupuesto Interno"]:
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                excel_dump += f"\n--- Pestaña: {sheet_name} ---\n"
                for row in ws.iter_rows(min_row=1, max_row=50, values_only=True):
                    # Filtrar filas vacías
                    if any(c is not None for c in row):
                        row_text = " | ".join(str(c) for c in row if c is not None)
                        excel_dump += row_text + "\n"
        
        prompt = f"""
Actúa como un controlador de costos de licitaciones.
A continuación tienes los requisitos mínimos extraídos del Pliego:
{req_text}

Y aquí tienes el volcado de datos (texto) del Excel de Costos completado por el equipo:
{excel_dump}

Tu tarea es revisar si hay incongruencias entre lo que pide el pliego y lo que se está cotizando en el Excel.
Por ejemplo: si el pliego pide 3 camionetas y en el Excel solo hay 1. Si pide un capataz y no figura en la mano de obra.
Devuelve un informe claro, listando en viñetas las INCONGRUENCIAS DETECTADAS. Si todo parece correcto, indícalo. No asumas errores por falta de formato, concéntrate en las CANTIDADES y CONCEPTOS.
"""
        response = self.llm_client.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
