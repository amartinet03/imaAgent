import os
import time
import requests
from typing import List, Dict, Optional

class MS365Client:
    """
    Cliente para interactuar con la Graph API de Microsoft 365 (App-Only permissions).
    """
    def __init__(self, tenant_id: str = None, client_id: str = None, client_secret: str = None):
        self.tenant_id = tenant_id or os.getenv("MSGRAPH_TENANT_ID")
        self.client_id = client_id or os.getenv("MSGRAPH_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("MSGRAPH_CLIENT_SECRET")
        self.token = None
        self.token_expires_at = 0
        
    def _get_access_token(self) -> str:
        """Obtiene o renueva el token de acceso OAuth 2.0 (Client Credentials Flow)."""
        if not self.tenant_id or not self.client_id or not self.client_secret:
            raise ValueError("Faltan credenciales de Microsoft Graph en el archivo .env")
            
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default"
        }
        
        response = requests.post(url, data=payload)
        response.raise_for_status()
        data = response.json()
        self.token = data.get("access_token")
        
        # El token suele expirar en 1 hora (3599 segundos). Restamos 60s por seguridad.
        expires_in = data.get("expires_in", 3599)
        self.token_expires_at = time.time() + expires_in - 60
        
        return self.token
        
    def get_auth_headers(self) -> dict:
        if not self.token or time.time() > self.token_expires_at:
            self._get_access_token()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def send_notification_email(self, user_email: str, subject: str, body: str) -> bool:
        """
        Envía un correo de notificación desde la casilla del usuario usando Graph API.
        Nota: Requiere permisos Mail.Send, o Mail.ReadWrite si solo se guarda en borradores.
        """
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/sendMail"
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": user_email
                        }
                    }
                ]
            },
            "saveToSentItems": "true"
        }
        
        # Enviar el correo
        response = requests.post(url, headers=self.get_auth_headers(), json=payload)
        
        if response.status_code == 202:
            print(f"Notificación enviada exitosamente a {user_email}")
            return True
        else:
            print(f"Error al enviar correo: {response.status_code} - {response.text}")
            return False

    def fetch_unread_tender_emails(self, user_email: str) -> List[Dict]:
        """
        Busca correos no leídos en la casilla.
        """
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages?$filter=isRead eq false"
        response = requests.get(url, headers=self.get_auth_headers())
        if response.status_code == 200:
            return response.json().get("value", [])
        print(f"Error al leer buzón de {user_email}: {response.status_code} - {response.text}")
        return []

    def get_email_attachments(self, user_email: str, message_id: str) -> List[Dict]:
        """
        Obtiene los adjuntos de un mensaje de correo específico.
        """
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}/attachments"
        response = requests.get(url, headers=self.get_auth_headers())
        if response.status_code == 200:
            return response.json().get("value", [])
        print(f"Error al obtener adjuntos: {response.status_code} - {response.text}")
        return []

    def mark_email_as_read(self, user_email: str, message_id: str) -> bool:
        """
        Marca un correo como leído para no volver a procesarlo.
        """
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}"
        payload = {
            "isRead": True
        }
        response = requests.patch(url, headers=self.get_auth_headers(), json=payload)
        if response.status_code == 200:
            return True
        print(f"Error al marcar correo como leído: {response.status_code} - {response.text}")
        return False

    def create_sharepoint_folder(self, site_id: str, drive_id: str, parent_item_id: str, folder_name: str) -> Optional[Dict]:
        """
        Crea una carpeta en una biblioteca de documentos (Drive) de SharePoint.
        Si parent_item_id es 'root', se crea en la raíz.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{parent_item_id}/children"
        payload = {
            "name": folder_name,
            "folder": { },
            "@microsoft.graph.conflictBehavior": "rename"
        }
        response = requests.post(url, headers=self.get_auth_headers(), json=payload)
        if response.status_code in [200, 201]:
            return response.json()
        print(f"Error al crear carpeta: {response.status_code} - {response.text}")
        return None

    def upload_file_to_sharepoint(self, site_id: str, drive_id: str, parent_item_id: str, file_name: str, file_content: bytes) -> Optional[Dict]:
        """
        Sube un archivo a una carpeta específica en SharePoint.
        Para archivos de hasta 4MB (Graph API simple upload).
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{parent_item_id}:/{file_name}:/content"
        headers = self.get_auth_headers()
        # Modificar el Content-Type solo para esta petición
        headers["Content-Type"] = "application/octet-stream"
        
        response = requests.put(url, headers=headers, data=file_content)
        if response.status_code in [200, 201]:
            return response.json()
        print(f"Error al subir archivo: {response.status_code} - {response.text}")
        return None

    def get_sharepoint_file_by_path(self, site_id: str, drive_id: str, item_path: str) -> bytes:
        """
        Descarga un archivo específico de una ruta de SharePoint.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{item_path}:/content"
        response = requests.get(url, headers=self.get_auth_headers())
        if response.status_code == 200:
            return response.content
        print(f"Error al descargar archivo desde {item_path}: {response.status_code} - {response.text}")
        return None
        
    def update_sharepoint_file_by_path(self, site_id: str, drive_id: str, item_path: str, file_content: bytes) -> bool:
        """
        Actualiza (o crea) un archivo en una ruta específica de SharePoint.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{item_path}:/content"
        headers = self.get_auth_headers()
        headers["Content-Type"] = "application/octet-stream"
        response = requests.put(url, headers=headers, data=file_content)
        if response.status_code in [200, 201]:
            return True
        print(f"Error al actualizar archivo en {item_path}: {response.status_code} - {response.text}")
        return False

    def setup_tender_sharepoint_folders(self, user_email: str, tender_name: str) -> Optional[str]:
        """
        Crea la estructura de carpetas en el OneDrive/SharePoint del usuario o en el Sitio especificado.
        Retorna el ID de la carpeta principal creada.
        """
        site_id = os.getenv("SHAREPOINT_TENDERS_SITE_ID")
        drive_id = os.getenv("SHAREPOINT_TENDERS_DRIVE_ID")
        
        # 1. Crear carpeta principal
        if site_id and drive_id:
            url_root = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"
        else:
            url_root = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root/children"
            
        payload_root = {
            "name": tender_name,
            "folder": { },
            "@microsoft.graph.conflictBehavior": "rename"
        }
        res = requests.post(url_root, headers=self.get_auth_headers(), json=payload_root)
        if res.status_code not in [200, 201]:
            print(f"Error creando carpeta principal: {res.text}")
            return None
            
        parent_id = res.json().get("id")
        
        # 2. Crear subcarpetas
        subfolders = ["ET", "OT", "OC", "Elementos de estudio"]
        if site_id and drive_id:
            url_children = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{parent_id}/children"
        else:
            url_children = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{parent_id}/children"
        
        for sub in subfolders:
            payload_sub = {
                "name": sub,
                "folder": { },
                "@microsoft.graph.conflictBehavior": "rename"
            }
            requests.post(url_children, headers=self.get_auth_headers(), json=payload_sub)
            
        return parent_id
        
    def upload_file_to_user_drive(self, user_email: str, parent_folder_id: str, subfolder_name: str, file_name: str, file_content: bytes):
        """
        Sube un archivo a una subcarpeta específica dentro de la carpeta principal de la licitación.
        """
        site_id = os.getenv("SHAREPOINT_TENDERS_SITE_ID")
        drive_id = os.getenv("SHAREPOINT_TENDERS_DRIVE_ID")
        
        # Primero necesitamos obtener el ID de la subcarpeta (ej: "ET")
        if site_id and drive_id:
            url_search = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{parent_folder_id}/children"
        else:
            url_search = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{parent_folder_id}/children"
            
        res = requests.get(url_search, headers=self.get_auth_headers())
        subfolder_id = None
        if res.status_code == 200:
            for item in res.json().get("value", []):
                if item.get("name") == subfolder_name:
                    subfolder_id = item.get("id")
                    break
                    
        if not subfolder_id:
            return None
            
        # Subir el archivo
        if site_id and drive_id:
            url_upload = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{subfolder_id}:/{file_name}:/content"
        else:
            url_upload = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{subfolder_id}:/{file_name}:/content"
            
        headers = self.get_auth_headers()
        headers["Content-Type"] = "application/octet-stream"
        
        res_up = requests.put(url_upload, headers=headers, data=file_content)
        if res_up.status_code in [200, 201]:
            return res_up.json()
        return None
