import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

def send_smtp_email(to_email: str, subject: str, body_html: str, body_plain: str = None) -> bool:
    """
    Envía un correo electrónico usando un servidor SMTP estándar (ej. Gmail).
    Incluye encabezados adecuados y formato multipart/alternative para evitar filtros de spam.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    
    if not smtp_user or not smtp_pass:
        print("Advertencia: Credenciales SMTP no configuradas. No se enviará el correo.")
        return False
        
    # Usar multipart/alternative es clave para no caer en spam
    msg = MIMEMultipart('alternative')
    
    # Agregar nombre a los correos ayuda a evitar el filtro de spam
    msg['From'] = f"ImaAgent Notificaciones <{smtp_user}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain="imaagent.local")
    
    # Si no se provee texto plano, generamos uno básico
    if not body_plain:
        body_plain = "Este mensaje requiere un cliente de correo con soporte HTML."
        
    # Adjuntar ambas versiones (el cliente de correo decide cuál mostrar, HTML preferentemente)
    part1 = MIMEText(body_plain, 'plain')
    part2 = MIMEText(body_html, 'html')
    
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"Correo enviado exitosamente a {to_email}")
        return True
    except Exception as e:
        print(f"Error al enviar correo SMTP: {e}")
        return False

def notify_analysis_completed(to_email: str, tender_id: int, cliente: str):
    subject = f"✅ Análisis completado: Licitación {tender_id} - {cliente}"
    
    body_plain = f"""
Análisis de Licitación Completado

El agente IA ha terminado de procesar los documentos de la licitación {tender_id} ({cliente}).
Ya puedes acceder a la plataforma para revisar las consultas, la oferta técnica y el costeo sugerido.

Este es un mensaje automático de ImaAgent.
"""

    body_html = f"""
    <html>
        <body>
            <h2 style="color: #2e6c80;">Análisis de Licitación Completado</h2>
            <p>El agente IA ha terminado de procesar los documentos de la licitación <strong>{tender_id} ({cliente})</strong>.</p>
            <p>Ya puedes acceder a la plataforma para revisar las consultas, la oferta técnica y el costeo sugerido.</p>
            <br/>
            <p style="color: #666; font-size: 12px;"><i>Este es un mensaje automático de ImaAgent.</i></p>
        </body>
    </html>
    """
    send_smtp_email(to_email, subject, body_html=body_html, body_plain=body_plain)
