import os
import requests
from typing import Optional

class CRMClient:
    """
    Cliente para interactuar con Pipedrive CRM.
    Permite actualizar el ciclo de vida de la cotización o gestionar la
    creación del negocio automáticamente.
    """
    def __init__(self, api_token: str = None):
        self.api_token = api_token or os.getenv("PIPEDRIVE_API_TOKEN")
        self.base_url = "https://api.pipedrive.com/v1"
        
    def create_deal(self, title: str, value: float = 0.0) -> Optional[str]:
        """
        Crea un nuevo negocio en el CRM.
        """
        url = f"{self.base_url}/deals?api_token={self.api_token}"
        payload = {
            "title": title,
            "value": value
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 201:
            data = response.json()
            return str(data.get("data", {}).get("id"))
        return None
        
    def update_deal_stage(self, deal_id: str, stage_id: int) -> bool:
        """
        Actualiza la etapa del negocio en Pipedrive mediante su stage_id.
        """
        url = f"{self.base_url}/deals/{deal_id}?api_token={self.api_token}"
        payload = {
            "stage_id": stage_id
        }
        
        response = requests.put(url, json=payload)
        return response.status_code == 200
