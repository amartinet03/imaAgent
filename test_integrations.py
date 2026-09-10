import os
from dotenv import load_dotenv
from src.integrations.crm_client import CRMClient
from src.integrations.ms365_client import MS365Client

# Cargar variables de entorno
load_dotenv()

def test_pipedrive():
    print("=== Probando Pipedrive CRM ===")
    crm = CRMClient()
    
    # 1. Crear un negocio de prueba
    deal_title = "Licitacion de Prueba IA"
    deal_id = crm.create_deal(title=deal_title, value=50000)
    
    if deal_id:
        print(f"[EXITO] Negocio creado exitosamente. ID del negocio: {deal_id}")
        print("   (Puedes ir a tu cuenta de Pipedrive y verificar si aparecio 'Licitacion de Prueba IA')")
    else:
        print("[ERROR] Error al crear el negocio en Pipedrive. Verifica el token en .env.")

def test_ms365():
    print("\n=== Probando Microsoft 365 (Graph API) ===")
    ms_client = MS365Client()
    
    # 1. Probar autenticacion
    try:
        token = ms_client._get_access_token()
        if token:
            print("[EXITO] Autenticacion exitosa. Se obtuvo el token de Microsoft.")
    except Exception as e:
        print(f"[ERROR] Error de autenticacion MS365: {e}")
        return

    # 2. Probar leer correos
    user_email = os.getenv("NOTIFY_EMAIL", "tucorreo@dominio.com") 
    print(f"\nBuscando correos no leidos en el buzon de: {user_email}")
    
    try:
        emails = ms_client.fetch_unread_tender_emails(user_email)
        print(f"[EXITO] Conexion al buzon exitosa. Se encontraron {len(emails)} correos no leidos.")
        
        # Si hay correos, intentar ver si el primero tiene adjuntos
        if emails:
            primer_correo_id = emails[0].get("id")
            subject = emails[0].get("subject", "Sin asunto")
            print(f"\nRevisando adjuntos del primer correo: '{subject}'")
            
            adjuntos = ms_client.get_email_attachments(user_email, primer_correo_id)
            print(f"[EXITO] El correo tiene {len(adjuntos)} adjunto(s).")
    except Exception as e:
        print(f"[ERROR] Error al leer correos: {e}")
        print("   (Esto suele pasar si la aplicacion en Azure AD no tiene permisos 'Mail.Read' otorgados).")

if __name__ == "__main__":
    test_pipedrive()
    test_ms365()
