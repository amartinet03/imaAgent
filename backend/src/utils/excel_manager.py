import os
import io
import openpyxl

def generate_client_abbreviation(client_name: str) -> str:
    """Generates a simple abbreviation if not found."""
    if not client_name or client_name.lower() == "desconocido":
        return "UNKNOWN"
    # Tomar primera palabra o letras clave
    words = client_name.upper().replace(".", "").replace(",", "").split()
    if len(words) >= 2:
        return (words[0][:3] + words[1][:2]).upper()
    return client_name[:5].upper()

def get_next_tender_info(ms_client, client_name: str) -> tuple:
    """
    Obtiene el próximo ID de licitación y la abreviación del cliente.
    Intenta usar SharePoint, si no están las credenciales/IDs configurados, 
    usa un mecanismo local de respaldo.
    """
    site_id = os.getenv("SHAREPOINT_COMERCIAL_SITE_ID")
    drive_id = os.getenv("SHAREPOINT_COMERCIAL_DRIVE_ID")
    
    # Rutas dentro del Drive (Document Library)
    id_file_path = "BD_Oportunidades.xlsx"
    clients_file_path = "Listado PipeDrive Clientes.xlsx"
    
    current_id = 1357 # Valor por defecto seguro (fallback)
    client_abbr = generate_client_abbreviation(client_name)
    
    if not site_id or not drive_id:
        print("⚠️ Advertencia: SHAREPOINT_SITE_ID o SHAREPOINT_DRIVE_ID no definidos en .env")
        print("Usando ID generado por Timestamp localmente y abreviación automática.")
        import time
        return int(time.time() % 10000), client_abbr

    try:
        # 1. Obtener y actualizar el ID
        id_file_bytes = ms_client.get_sharepoint_file_by_path(site_id, drive_id, id_file_path)
        if id_file_bytes:
            wb_id = openpyxl.load_workbook(io.BytesIO(id_file_bytes))
            # Buscar hoja ID_DEALS
            if "ID_DEALS" in wb_id.sheetnames:
                ws_id = wb_id["ID_DEALS"]
                # Asumimos que el ID está en B2 (Fila 2, Columna 2) o buscamos
                last_id = ws_id.cell(row=2, column=2).value
                if isinstance(last_id, (int, float)):
                    current_id = int(last_id) + 1
                else:
                    current_id += 1
                
                # Escribir el nuevo ID
                ws_id.cell(row=2, column=2, value=current_id)
                
                # Guardar y subir
                out_id = io.BytesIO()
                wb_id.save(out_id)
                ms_client.update_sharepoint_file_by_path(site_id, drive_id, id_file_path, out_id.getvalue())
                print(f"✅ ID actualizado en SharePoint: {current_id}")
            else:
                print(f"❌ Hoja 'ID_DEALS' no encontrada en {id_file_path}")
        else:
            print(f"❌ Archivo {id_file_path} no encontrado en SharePoint.")

        # 2. Obtener y actualizar Abreviatura del Cliente
        cli_file_bytes = ms_client.get_sharepoint_file_by_path(site_id, drive_id, clients_file_path)
        if cli_file_bytes:
            wb_cli = openpyxl.load_workbook(io.BytesIO(cli_file_bytes))
            ws_cli = wb_cli.active
            
            found = False
            first_empty_row = 1
            # Buscar cliente en columna 1 (A), asumiendo abreviación en columna 2 (B)
            for row in range(1, ws_cli.max_row + 2):
                cell_val = ws_cli.cell(row=row, column=1).value
                if not cell_val:
                    if first_empty_row == 1:
                        first_empty_row = row
                    break
                
                if str(cell_val).strip().lower() == str(client_name).strip().lower():
                    found = True
                    abbr_val = ws_cli.cell(row=row, column=2).value
                    if abbr_val:
                        client_abbr = str(abbr_val).strip()
                    break
            
            if not found:
                print(f"ℹ️ Cliente '{client_name}' no encontrado. Añadiendo con abreviatura '{client_abbr}'")
                ws_cli.cell(row=first_empty_row, column=1, value=client_name)
                ws_cli.cell(row=first_empty_row, column=2, value=client_abbr)
                
                out_cli = io.BytesIO()
                wb_cli.save(out_cli)
                ms_client.update_sharepoint_file_by_path(site_id, drive_id, clients_file_path, out_cli.getvalue())
        else:
            print(f"❌ Archivo {clients_file_path} no encontrado en SharePoint.")
            
    except Exception as e:
        print(f"Error procesando Excels en SharePoint: {e}")
        
    return current_id, client_abbr
