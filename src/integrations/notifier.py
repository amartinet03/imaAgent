import os
import re
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

def send_ms365_email(to_email: str, subject: str, body_html: str, sender_email: str = None) -> bool:
    """
    Envía un correo electrónico a través de Microsoft 365 (Graph API)
    usando la casilla corporativa oficial (por defecto sgih@ima-si.com.ar).
    Requiere permiso de aplicación 'Mail.Send' con consentimiento de administrador en Azure.
    """
    sender = sender_email or os.getenv("MS365_SENDER_EMAIL", "sgih@ima-si.com.ar")
    try:
        from src.integrations.ms365_client import MS365Client
        client = MS365Client()
        headers = client.get_auth_headers()
        url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body_html
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            },
            "saveToSentItems": "true"
        }
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code in (200, 202):
            print(f"[M365] Correo enviado exitosamente desde {sender} a {to_email}")
            return True
        else:
            print(f"[M365] Graph API rechazó el envío (Status {res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"[M365] Excepción enviando correo Graph API: {e}")
        return False

def send_smtp_email(to_email: str, subject: str, body_html: str, body_plain: str = None) -> bool:
    """
    Envía un correo electrónico usando un servidor SMTP estándar como fallback.
    Establece 'sgih@ima-si.com.ar' en los encabezados From y Reply-To.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("MS365_SENDER_EMAIL", "sgih@ima-si.com.ar")
    sender_name = os.getenv("SENDER_DISPLAY_NAME", "IMA Licitaciones")
    
    if not smtp_user or not smtp_pass:
        print("Advertencia: Credenciales SMTP no configuradas. No se enviará el correo.")
        return False
        
    msg = MIMEMultipart('alternative')
    msg['From'] = f"{sender_name} <{sender_email}>"
    msg['Reply-To'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain="ima-si.com.ar")
    
    if not body_plain:
        body_plain = "Este mensaje requiere un cliente de correo con soporte HTML."
        
    part1 = MIMEText(body_plain, 'plain', 'utf-8')
    part2 = MIMEText(body_html, 'html', 'utf-8')
    
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"[SMTP Fallback] Correo enviado exitosamente a {to_email}")
        return True
    except Exception as e:
        print(f"Error al enviar correo SMTP: {e}")
        return False

def notify_analysis_completed(to_email: str, tender_id: int, cliente: str = None, tender_title: str = None):
    """
    Envía la notificación de análisis completado.
    - Utiliza exclusivamente el título oficial de la licitación (sin números internos).
    - Prioriza el envío a través de Microsoft 365 desde sgih@ima-si.com.ar.
    - Si M365 aún no tiene el permiso Mail.Send autorizado en Azure, utiliza SMTP de respaldo con encabezado From: sgih@ima-si.com.ar.
    """
    # Determinar el título limpio de la licitación (sin prefijos de IDs internos)
    display_title = (tender_title or cliente or f"Licitación {tender_id}").strip()
    
    # Limpiar si trae prefijos antiguos de 'Licitación XX - ' o similar
    cleaned_title = re.sub(r'^(?:Licitaci[oó]n\s*\d+\s*[-:]?\s*)+', '', display_title, flags=re.IGNORECASE).strip()
    if not cleaned_title:
        cleaned_title = display_title

    subject = f"✅ Análisis completado: {cleaned_title}"
    
    body_plain = f"""Análisis de Licitación Completado

El agente IA ha terminado de procesar los documentos de la licitación:
{cleaned_title}

Ya puedes acceder a la plataforma para revisar las consultas, la oferta técnica y el costeo sugerido.

Este es un mensaje automático de IMA Agent.
"""

    body_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
        <div style="background-color: #0f172a; padding: 20px 24px; border-bottom: 2px solid #2563eb;">
            <div style="font-size: 26px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px;">
                <span style="color: #a3e635;">i</span>ma
            </div>
            <div style="font-size: 10px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px;">
                SI | Argentina Holdas Latam
            </div>
        </div>
        
        <div style="padding: 28px 24px;">
            <h2 style="color: #2563eb; margin-top: 0; margin-bottom: 12px; font-size: 18px; font-weight: 800;">
                ✓ Análisis de Licitación Completado
            </h2>
            <p style="font-size: 14px; color: #475569; margin-bottom: 16px; line-height: 1.5;">
                El agente IA ha terminado de procesar todos los documentos, requerimientos y especificaciones de la licitación:
            </p>
            
            <div style="background-color: #f1f5f9; border-left: 4px solid #2563eb; padding: 14px 16px; border-radius: 8px; margin: 18px 0; font-size: 15px; font-weight: 700; color: #0f172a; line-height: 1.4;">
                {cleaned_title}
            </div>
            
            <p style="font-size: 14px; color: #475569; line-height: 1.5;">
                Ya puedes acceder a la plataforma para revisar las consultas al pliego, la oferta técnica ensamblada y el costeo sugerido.
            </p>
            
            <div style="margin-top: 28px; padding-top: 16px; border-top: 1px solid #f1f5f9; color: #94a3b8; font-size: 11px;">
                Mensaje automático enviado por <strong>IMA Agent</strong> • Casilla oficial: sgih@ima-si.com.ar
            </div>
        </div>
    </div>
</body>
</html>"""

    # 1. Intentar envío nativo por Microsoft 365 Graph API (desde sgih@ima-si.com.ar)
    m365_success = send_ms365_email(to_email, subject, body_html=body_html)
    if m365_success:
        return True

    # 2. Si M365 aún no tiene el permiso Mail.Send concedido, usar SMTP de respaldo
    print("[Notifier] Usando fallback SMTP para garantizar entrega de la notificación...")
    return send_smtp_email(to_email, subject, body_html=body_html, body_plain=body_plain)


def notify_weekly_radar_digest(to_email: str, pending_opps: list) -> bool:
    """
    Envía el resumen semanal (cada viernes) de las licitaciones detectadas
    por el Radar que aún no han sido analizadas ni descartadas por el usuario.
    """
    if not pending_opps:
        print("[Notifier] No hay oportunidades pendientes para enviar en el resumen semanal.")
        return False

    count = len(pending_opps)
    subject = f"📡 Radar de Licitaciones: Resumen semanal de oportunidades pendientes ({count})"

    items_html = ""
    items_plain = ""
    for idx, opp in enumerate(pending_opps, 1):
        p_name = opp.get("portal_name", "Portal Oficial")
        title = opp.get("title", "Licitación sin título")
        url = opp.get("url", "#")
        kw = opp.get("matched_keywords", "")
        snippet = opp.get("snippet", "")

        items_plain += f"{idx}. [{p_name}] {title}\n   URL: {url}\n   Palabras clave: {kw}\n\n"

        items_html += f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-bottom: 12px;">
            <div style="margin-bottom: 8px;">
                <span style="background-color: #dbeafe; color: #1e40af; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; text-transform: uppercase;">
                    {p_name}
                </span>
                <span style="font-size: 11px; color: #64748b; font-weight: 600; margin-left: 8px;">
                    Coincidencias: {kw}
                </span>
            </div>
            <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 6px;">
                <a href="{url}" style="color: #2563eb; text-decoration: none;" target="_blank">
                    {title}
                </a>
            </div>
            {f'<div style="font-size: 12px; color: #64748b; line-height: 1.4; margin-top: 4px;">{snippet}</div>' if snippet else ''}
        </div>
        """

    body_plain = f"""Radar de Licitaciones - Resumen Semanal de los Viernes

Hola,

El Radar de IMA ha detectado {count} oportunidades de compras y licitaciones en portales oficiales que aún no has revisado o procesado:

{items_plain}
Ingresa a la plataforma IMA Agent en la sección 'Radar de Licitaciones' para analizarlas con IA o descartarlas.

Mensaje automático semanal de IMA Agent • sgih@ima-si.com.ar
"""

    body_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
    <div style="max-width: 650px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
        <div style="background-color: #0f172a; padding: 20px 24px; border-bottom: 2px solid #2563eb;">
            <div style="font-size: 26px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px;">
                <span style="color: #a3e635;">i</span>ma
            </div>
            <div style="font-size: 10px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px;">
                SI | Argentina Holdas Latam
            </div>
        </div>
        
        <div style="padding: 28px 24px;">
            <h2 style="color: #0f172a; margin: 0 0 8px 0; font-size: 18px; font-weight: 800;">
                📡 Resumen Semanal: Radar de Licitaciones
            </h2>
            <p style="font-size: 13px; color: #64748b; margin-top: 4px; margin-bottom: 20px; line-height: 1.5;">
                Se han detectado <strong>{count}</strong> oportunidades de licitación en portales públicos oficiales que coinciden con tus palabras clave técnicas y están pendientes de revisión:
            </p>
            
            <div style="margin-bottom: 24px;">
                {items_html}
            </div>
            
            <p style="font-size: 13px; color: #475569; line-height: 1.5;">
                Ingresa a la sección <strong>Radar de Licitaciones</strong> en la plataforma para decidir si <em>iniciar el análisis automático ("El Show")</em> o <em>descartarlas permanentemente</em>.
            </p>
            
            <div style="margin-top: 28px; padding-top: 16px; border-top: 1px solid #f1f5f9; color: #94a3b8; font-size: 11px;">
                Mensaje automático semanal enviado por <strong>IMA Agent</strong> • Casilla oficial: sgih@ima-si.com.ar
            </div>
        </div>
    </div>
</body>
</html>"""

    m365_success = send_ms365_email(to_email, subject, body_html=body_html)
    if m365_success:
        print(f"[Notifier] Resumen semanal enviado con éxito a {to_email} vía M365.")
        return True

    print("[Notifier] Usando fallback SMTP para resumen semanal...")
    return send_smtp_email(to_email, subject, body_html=body_html, body_plain=body_plain)

