import os

class SharePointClient:
    """
    Cliente para interactuar con SharePoint.
    Se encarga de automatizar la creación de la estructura de carpetas de las licitaciones
    (ET, OT, OC, elementos de estudio) y subir los documentos procesados por la IA.
    """
    def __init__(self, site_url: str = None):
        self.site_url = site_url or os.getenv("SHAREPOINT_SITE_URL")
        # TODO: Autenticación mediante MSAL o biblioteca Office365-REST-Python-Client
        
    def create_tender_folder_structure(self, tender_id: str, tender_name: str) -> str:
        """
        Crea la estructura de carpetas base para una licitación.
        Ej: /Licitaciones/1234_Licitacion_Pisos/
             ├── ET (Especificación Técnica)
             ├── OT (Oferta Técnica)
             ├── OC (Oferta Comercial)
             └── elementos de estudio
        Devuelve la URL o ruta principal de la carpeta creada.
        """
        # TODO: Implementar creación de carpetas
        return f"{self.site_url}/Licitaciones/{tender_id}_{tender_name}"
        
    def upload_file(self, local_file_path: str, sharepoint_folder_path: str) -> bool:
        """
        Sube un archivo local a una ruta específica de SharePoint.
        """
        # TODO: Implementar subida de archivo
        return True
