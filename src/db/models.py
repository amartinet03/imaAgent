import sqlite3
import os
import json
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'tender_db.sqlite')

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'PENDIENTE',
            parsed_data TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER,
            role TEXT,
            content TEXT,
            chat_type TEXT DEFAULT 'GENERAL',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(tender_id) REFERENCES tenders(id)
        )
    ''')

    # Tablas para el Radar de Licitaciones Web
    c.execute('''
        CREATE TABLE IF NOT EXISTS monitored_portals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            frequency TEXT DEFAULT 'Diaria',
            active INTEGER DEFAULT 1,
            last_scanned TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS monitored_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS radar_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portal_name TEXT,
            title TEXT NOT NULL,
            url TEXT,
            matched_keywords TEXT,
            snippet TEXT,
            status TEXT DEFAULT 'PENDIENTE',
            tender_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(portal_name, title)
        )
    ''')

    # Tabla de Usuarios y Contraseñas
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de Parámetros Globales (Settings)
    c.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Por defecto el daemon de automatización está apagado ('0')
    c.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('daemon_active', '0')")

    # Poblar usuario admin inicial si no existe
    admin_default_hash = hash_password("Ima2026!")
    c.execute("INSERT OR IGNORE INTO users (username, password_hash) VALUES ('admin', ?)", (admin_default_hash,))

    # Poblar portales por defecto si no existen
    c.execute("SELECT COUNT(*) FROM monitored_portals")
    if c.fetchone()[0] == 0:
        default_portals = [
            ("NA-SA (Nucleoeléctrica Argentina)", "https://www.na-sa.com.ar/proveedores/home/licitaciones/vigentes", "Diaria"),
            ("ARSAT", "https://www.arsat.com.ar/acerca-de-arsat/transparencia-activa/compras-y-contrataciones/", "Diaria")
        ]
        c.executemany("INSERT OR IGNORE INTO monitored_portals (name, url, frequency) VALUES (?, ?, ?)", default_portals)

    # Poblar palabras clave base solicitadas por el usuario
    c.execute("SELECT COUNT(*) FROM monitored_keywords")
    if c.fetchone()[0] == 0:
        default_keywords = [
            ("servicio",),
            ("mantenimiento",),
            ("limpieza",),
            ("facility",),
            ("aire acondicionado",),
            ("piping",),
            ("montaje",),
            ("soldadura",),
            ("electromecánico",),
            ("obra",)
        ]
        c.executemany("INSERT OR IGNORE INTO monitored_keywords (keyword) VALUES (?)", default_keywords)

    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        import hashlib
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_user_credentials(username: str, password: str) -> bool:
    if not username or not password:
        return False
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        stored_hash = row[0]
        # 1. Comprobar si es un hash bcrypt (formato $2b$ o $2a$)
        if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
            try:
                import bcrypt
                return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
            except Exception:
                return False
        # 2. Compatibilidad retroactiva: comprobar hash legacy SHA-256
        import hashlib
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if stored_hash == legacy_hash:
            # Auto-migrar la clave a bcrypt para mayor seguridad
            update_user_password(username, password)
            return True
        return False
    return False

def update_user_password(username: str, new_password: str) -> bool:
    if not username or not new_password:
        return False
    conn = get_connection()
    c = conn.cursor()
    p_hash = hash_password(new_password)
    c.execute('''
        INSERT INTO users (username, password_hash, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash, updated_at = CURRENT_TIMESTAMP
    ''', (username, p_hash))
    conn.commit()
    conn.close()
    return True

def get_app_setting(key: str, default: str = None) -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    if row is not None:
        return row[0]
    return default

def set_app_setting(key: str, value: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    ''', (key, str(value)))
    conn.commit()
    conn.close()

def is_daemon_active() -> bool:
    return get_app_setting("daemon_active", "0") == "1"

def set_daemon_active(active: bool):
    set_app_setting("daemon_active", "1" if active else "0")

def create_tender(name: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO tenders (name, status) VALUES (?, 'PROCESANDO')", (name,))
    tender_id = c.lastrowid
    conn.commit()
    conn.close()
    return tender_id

def get_all_tenders():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tenders ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_tender(tender_id: int):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,))
    row = c.fetchone()
    conn.close()
    if row:
        tender = dict(row)
        if tender['parsed_data']:
            tender['parsed_data'] = json.loads(tender['parsed_data'])
        return tender
    return None

def update_tender_status(tender_id: int, status: str, parsed_data: dict = None, error_message: str = None):
    conn = get_connection()
    c = conn.cursor()
    
    if parsed_data is not None:
        c.execute("UPDATE tenders SET status = ?, parsed_data = ? WHERE id = ?", 
                  (status, json.dumps(parsed_data, ensure_ascii=False), tender_id))
    elif error_message is not None:
        c.execute("UPDATE tenders SET status = ?, error_message = ? WHERE id = ?", 
                  (status, error_message, tender_id))
    else:
        c.execute("UPDATE tenders SET status = ? WHERE id = ?", (status, tender_id))
        
    conn.commit()
    conn.close()

def update_tender_parsed_data(tender_id: int, parsed_data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE tenders SET parsed_data = ? WHERE id = ?", 
              (json.dumps(parsed_data, ensure_ascii=False), tender_id))
    conn.commit()
    conn.close()

def add_message(tender_id: int, role: str, content: str, chat_type: str = 'GENERAL'):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO messages (tender_id, role, content, chat_type) VALUES (?, ?, ?, ?)", 
              (tender_id, role, content, chat_type))
    conn.commit()
    conn.close()

def get_messages(tender_id: int, chat_type: str = 'GENERAL'):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE tender_id = ? AND chat_type = ? ORDER BY created_at ASC", (tender_id, chat_type))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_tender(tender_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE tender_id = ?", (tender_id,))
    c.execute("DELETE FROM tenders WHERE id = ?", (tender_id,))
    conn.commit()
    conn.close()

# --- Funciones para el Radar de Licitaciones Web ---

def get_monitored_portals():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM monitored_portals ORDER BY created_at ASC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_monitored_portal(name: str, url: str, frequency: str = "Diaria") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO monitored_portals (name, url, frequency, active) VALUES (?, ?, ?, 1)", 
              (name.strip(), url.strip(), frequency))
    portal_id = c.lastrowid
    conn.commit()
    conn.close()
    return portal_id

def delete_monitored_portal(portal_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM monitored_portals WHERE id = ?", (portal_id,))
    conn.commit()
    conn.close()

def toggle_monitored_portal(portal_id: int, active: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE monitored_portals SET active = ? WHERE id = ?", (active, portal_id))
    conn.commit()
    conn.close()

def update_portal_scanned_time(portal_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE monitored_portals SET last_scanned = CURRENT_TIMESTAMP WHERE id = ?", (portal_id,))
    conn.commit()
    conn.close()

def get_monitored_keywords():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM monitored_keywords ORDER BY keyword ASC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_monitored_keyword(keyword: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO monitored_keywords (keyword) VALUES (?)", (keyword.strip().lower(),))
    kw_id = c.lastrowid
    conn.commit()
    conn.close()
    return kw_id

def delete_monitored_keyword(kw_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM monitored_keywords WHERE id = ?", (kw_id,))
    conn.commit()
    conn.close()

def save_radar_opportunity(portal_name: str, title: str, url: str, matched_keywords: str, snippet: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO radar_opportunities (portal_name, title, url, matched_keywords, snippet, status)
        VALUES (?, ?, ?, ?, ?, 'PENDIENTE')
    ''', (portal_name, title.strip(), url.strip(), matched_keywords, snippet.strip()))
    opp_id = c.lastrowid
    conn.commit()
    conn.close()
    return opp_id

def get_pending_opportunities():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM radar_opportunities WHERE status = 'PENDIENTE' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_opportunities():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM radar_opportunities ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_opportunity_status(opp_id: int, status: str, tender_id: int = None):
    conn = get_connection()
    c = conn.cursor()
    if tender_id is not None:
        c.execute("UPDATE radar_opportunities SET status = ?, tender_id = ? WHERE id = ?", (status, tender_id, opp_id))
    else:
        c.execute("UPDATE radar_opportunities SET status = ? WHERE id = ?", (status, opp_id))
    conn.commit()
    conn.close()

