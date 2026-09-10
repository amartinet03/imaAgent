import os
from dotenv import load_dotenv
from src.integrations.ms365_client import MS365Client
import requests

load_dotenv()

def debug_graph():
    ms_client = MS365Client()
    try:
        token = ms_client._get_access_token()
        print("Token obtenido!")
    except Exception as e:
        print("Error auth:", e)
        return
        
    user_email = os.getenv("MS365_MONITOR_EMAIL", "Sebastien.martinet@ima-si.com.ar")
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages?$filter=isRead eq false"
    print(f"Requesting: {url}")
    
    response = requests.get(url, headers=ms_client.get_auth_headers())
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error Response: {response.text}")
    else:
        data = response.json()
        print(f"Success! Encontrados {len(data.get('value', []))} mensajes.")

debug_graph()
