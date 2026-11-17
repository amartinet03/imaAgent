import os
import sys
import time
import threading
import datetime
from src.db.models import (
    get_pending_opportunities,
    get_daemon_settings,
    set_daemon_setting
)
from src.core.web_scanner import WebTenderScanner
from src.integrations.notifier import notify_weekly_radar_digest

_radar_thread = None
_radar_running = False

def check_and_send_friday_digest(force: bool = False) -> dict:
    """
    Verifica si corresponde enviar el resumen semanal de oportunidades de los viernes.
    Si force=True, lo envía inmediatamente independientemente del día.
    """
    now = datetime.datetime.now()
    is_friday = (now.weekday() == 4)  # 4 = Friday
    current_week_key = now.strftime("%Y_W%W")
    
    settings = get_daemon_settings()
    last_sent_week = settings.get("last_friday_digest_week", "")

    if not is_friday and not force:
        return {
            "sent": False,
            "reason": f"Hoy no es viernes (es día {now.strftime('%A')}).",
            "is_friday": False,
            "current_week": current_week_key,
            "last_sent_week": last_sent_week
        }

    if last_sent_week == current_week_key and not force:
        return {
            "sent": False,
            "reason": f"El resumen semanal de la semana {current_week_key} ya fue enviado previamente.",
            "is_friday": is_friday,
            "current_week": current_week_key,
            "last_sent_week": last_sent_week
        }

    pending_opps = get_pending_opportunities()
    if not pending_opps:
        return {
            "sent": False,
            "reason": "No hay oportunidades en estado PENDIENTE para notificar.",
            "is_friday": is_friday,
            "current_week": current_week_key,
            "pending_count": 0
        }

    recipient = os.getenv("NOTIFY_EMAIL", "sebastien.martinet@ima-si.com.ar")
    print(f"[Radar Scheduler] Enviando resumen semanal de {len(pending_opps)} oportunidades a {recipient}...")
    
    success = notify_weekly_radar_digest(recipient, pending_opps)
    if success:
        set_daemon_setting("last_friday_digest_week", current_week_key)
        set_daemon_setting("last_friday_digest_time", now.isoformat())
        return {
            "sent": True,
            "recipient": recipient,
            "pending_count": len(pending_opps),
            "week": current_week_key,
            "timestamp": now.isoformat()
        }
    else:
        return {
            "sent": False,
            "reason": "Error en el servicio de correo al despachar el resumen semanal.",
            "is_friday": is_friday,
            "pending_count": len(pending_opps)
        }


def radar_background_worker():
    """
    Ciclo continuo del Radar en segundo plano:
    1. Escaneo periódico de portales oficiales cada 2 horas.
    2. Chequeo y envío del resumen semanal de los viernes.
    """
    global _radar_running
    print("=== [Radar Scheduler] Iniciando hilo continuo de monitoreo del Radar ===")
    _radar_running = True
    
    # Pausa inicial corta de 10 segundos tras levantar el servidor
    time.sleep(10)
    
    scanner = WebTenderScanner()

    while _radar_running:
        try:
            print("[Radar Scheduler] Ejecutando escaneo automático de portales oficiales...")
            scan_res = scanner.scan_all_portals()
            print(f"[Radar Scheduler] Escaneo completado: {scan_res.get('total_found', 0)} licitaciones analizadas ({scan_res.get('new_detected_count', 0)} nuevas guardadas).")
        except Exception as e:
            print(f"[Radar Scheduler Error] Error en escaneo de portales: {e}")

        try:
            # Chequeo de viernes
            check_and_send_friday_digest(force=False)
        except Exception as e:
            print(f"[Radar Scheduler Error] Error al verificar envío semanal: {e}")

        # Dormir 2 horas (7200 segundos) entre chequeos periódicos
        for _ in range(720):
            if not _radar_running:
                break
            time.sleep(10)

    print("=== [Radar Scheduler] Hilo continuo de Radar detenido ===")


def start_radar_scheduler():
    """
    Lanza el scheduler en segundo plano si aún no está en ejecución.
    """
    global _radar_thread
    if _radar_thread is not None and _radar_thread.is_alive():
        print("[Radar Scheduler] El hilo de monitoreo ya está activo.")
        return

    _radar_thread = threading.Thread(target=radar_background_worker, daemon=True, name="RadarBackgroundWorker")
    _radar_thread.start()
    print("[Radar Scheduler] Hilo en segundo plano lanzado exitosamente.")
