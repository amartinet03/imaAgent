import os
import re
import json
import time
import datetime
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
# Cargar variables de entorno tanto desde backend/.env como desde el root .env
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_root = os.path.dirname(os.path.dirname(_current_dir))
load_dotenv(os.path.join(_backend_root, ".env"), override=False)
load_dotenv(os.path.join(os.path.dirname(_backend_root), ".env"), override=False)

def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/imaagent_db")

SQLITE_PATH = os.path.join(_backend_root, 'data', 'tender_db.sqlite')

_USE_POSTGRES = None

def get_connection(retries: int = 1, delay: float = 1.0):
    """
    Obtiene una conexión a la base de datos.
    Prioriza PostgreSQL si DATABASE_URL está configurado.
    Si falla, recurre a SQLite como fallback de alta disponibilidad.
    """
    global _USE_POSTGRES
    db_url = get_database_url()

    # Intentar PostgreSQL
    if db_url and not db_url.startswith("sqlite"):
        for attempt in range(retries):
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                conn = psycopg2.connect(db_url, connect_timeout=5)
                _USE_POSTGRES = True
                return conn, "postgres"
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    if _USE_POSTGRES is not False:
                        print(f"[DB Warning] No se pudo conectar a PostgreSQL ({e}). Usando SQLite fallback.", flush=True)
                    _USE_POSTGRES = False

    # Fallback SQLite
    import sqlite3
    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn, "sqlite"

def hash_password(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        import hashlib
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db(max_retries: int = 5, retry_delay: float = 1.5):
    print("=== [IMA-AGENT DEBUG] Inicializando Base de Datos ===", flush=True)
    conn, engine = get_connection(retries=max_retries, delay=retry_delay)
    c = conn.cursor()

    if engine == "postgres":
        # Tablas PostgreSQL
        c.execute('''
            CREATE TABLE IF NOT EXISTS tenders (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'PENDIENTE',
                parsed_data TEXT,
                error_message TEXT,
                progress INTEGER DEFAULT 0,
                progress_msg TEXT DEFAULT 'Iniciando...',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                tender_id INTEGER REFERENCES tenders(id) ON DELETE CASCADE,
                role TEXT,
                content TEXT,
                chat_type TEXT DEFAULT 'GENERAL',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitored_portals (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                frequency TEXT DEFAULT 'Diaria',
                active INTEGER DEFAULT 1,
                last_scanned TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS monitored_keywords (
                id SERIAL PRIMARY KEY,
                keyword TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS radar_opportunities (
                id SERIAL PRIMARY KEY,
                portal_name TEXT,
                title TEXT NOT NULL,
                url TEXT,
                matched_keywords TEXT,
                snippet TEXT,
                status TEXT DEFAULT 'PENDIENTE',
                tender_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(portal_name, title)
            );
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS radar_tombstones (
                id SERIAL PRIMARY KEY,
                portal_name TEXT,
                title TEXT,
                url TEXT,
                reason TEXT DEFAULT 'ELIMINADA',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_radar_tombstones_url ON radar_tombstones(url);
            CREATE INDEX IF NOT EXISTS idx_radar_tombstones_title ON radar_tombstones(portal_name, title);
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Poblar configuración inicial y admin
        c.execute("INSERT INTO app_settings (key, value) VALUES ('daemon_active', '0') ON CONFLICT (key) DO NOTHING;")
        admin_hash = hash_password("Ima2026!")
        c.execute("INSERT INTO users (username, password_hash) VALUES ('admin', %s) ON CONFLICT (username) DO NOTHING;", (admin_hash,))

        c.execute("SELECT value FROM app_settings WHERE key = 'initial_setup_done'")
        row = c.fetchone()
        if not row:
            default_portals = [
                ("NA-SA (Nucleoeléctrica Argentina)", "https://www.na-sa.com.ar/proveedores/home/licitaciones/vigentes", "Diaria"),
                ("ARSAT", "https://www.arsat.com.ar/acerca-de-arsat/transparencia-activa/compras-y-contrataciones/", "Diaria")
            ]
            for p in default_portals:
                c.execute("INSERT INTO monitored_portals (name, url, frequency) VALUES (%s, %s, %s) ON CONFLICT (url) DO NOTHING;", p)

            default_keywords = [
                "servicio", "mantenimiento", "limpieza", "facility", "aire acondicionado",
                "piping", "montaje", "soldadura", "electromecánico", "obra"
            ]
            for kw in default_keywords:
                c.execute("INSERT INTO monitored_keywords (keyword) VALUES (%s) ON CONFLICT (keyword) DO NOTHING;", (kw,))

            c.execute("INSERT INTO app_settings (key, value) VALUES ('initial_setup_done', '1') ON CONFLICT (key) DO NOTHING;")

    else:
        # SQLite
        c.execute('''
            CREATE TABLE IF NOT EXISTS tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'PENDIENTE',
                parsed_data TEXT,
                error_message TEXT,
                progress INTEGER DEFAULT 0,
                progress_msg TEXT DEFAULT 'Iniciando...',
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS radar_tombstones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portal_name TEXT,
                title TEXT,
                url TEXT,
                reason TEXT DEFAULT 'ELIMINADA',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_radar_tombstones_url ON radar_tombstones(url)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_radar_tombstones_title ON radar_tombstones(portal_name, title)')
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('daemon_active', '0')")
        admin_hash = hash_password("Ima2026!")
        c.execute("INSERT OR IGNORE INTO users (username, password_hash) VALUES ('admin', ?)", (admin_hash,))

        c.execute("SELECT value FROM app_settings WHERE key = 'initial_setup_done'")
        row = c.fetchone()
        if not row:
            default_portals = [
                ("NA-SA (Nucleoeléctrica Argentina)", "https://www.na-sa.com.ar/proveedores/home/licitaciones/vigentes", "Diaria"),
                ("ARSAT", "https://www.arsat.com.ar/acerca-de-arsat/transparencia-activa/compras-y-contrataciones/", "Diaria")
            ]
            c.executemany("INSERT OR IGNORE INTO monitored_portals (name, url, frequency) VALUES (?, ?, ?)", default_portals)
            default_keywords = [
                ("servicio",), ("mantenimiento",), ("limpieza",), ("facility",), ("aire acondicionado",),
                ("piping",), ("montaje",), ("soldadura",), ("electromecánico",), ("obra",)
            ]
            c.executemany("INSERT OR IGNORE INTO monitored_keywords (keyword) VALUES (?)", default_keywords)
            c.execute("INSERT INTO app_settings (key, value) VALUES ('initial_setup_done', '1')")

    conn.commit()
    conn.close()
    print(f"=== [IMA-AGENT DEBUG] Base de Datos Inicializada con éxito ({engine.upper()}) ===", flush=True)

def verify_user_credentials(username: str, password: str) -> bool:
    if not username or not password:
        return False
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"SELECT password_hash FROM users WHERE username = {ph}", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        stored_hash = row[0]
        if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
            try:
                import bcrypt
                return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
            except Exception:
                return False
        import hashlib
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if stored_hash == legacy_hash:
            update_user_password(username, password)
            return True
    return False

def update_user_password(username: str, new_password: str) -> bool:
    if not username or not new_password:
        return False
    conn, engine = get_connection()
    c = conn.cursor()
    p_hash = hash_password(new_password)
    if engine == "postgres":
        c.execute('''
            INSERT INTO users (username, password_hash, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT(username) DO UPDATE SET password_hash = EXCLUDED.password_hash, updated_at = CURRENT_TIMESTAMP
        ''', (username, p_hash))
    else:
        c.execute('''
            INSERT INTO users (username, password_hash, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash, updated_at = CURRENT_TIMESTAMP
        ''', (username, p_hash))
    conn.commit()
    conn.close()
    return True

def get_app_setting(key: str, default: str = None) -> Optional[str]:
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"SELECT value FROM app_settings WHERE key = {ph}", (key,))
    row = c.fetchone()
    conn.close()
    if row is not None:
        return row[0]
    return default

def set_app_setting(key: str, value: str):
    conn, engine = get_connection()
    c = conn.cursor()
    if engine == "postgres":
        c.execute('''
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        ''', (key, str(value)))
    else:
        c.execute('''
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        ''', (key, str(value)))
    conn.commit()
    conn.close()

def get_daemon_settings() -> dict:
    return {
        'mail': get_app_setting("daemon_mail", "0") == "1",
        'sharepoint': get_app_setting("daemon_sharepoint", "0") == "1",
        'pipedrive': get_app_setting("daemon_pipedrive", "0") == "1",
        'ai': get_app_setting("daemon_ai", "0") == "1"
    }

def set_daemon_setting(key: str, active: bool):
    set_app_setting(f"daemon_{key}", "1" if active else "0")

def is_daemon_active() -> bool:
    return any(get_daemon_settings().values()) or (get_app_setting("daemon_active", "0") == "1")

def set_daemon_active(active: bool):
    val = "1" if active else "0"
    set_app_setting("daemon_active", val)
    for k in ['mail', 'sharepoint', 'pipedrive', 'ai']:
        set_app_setting(f"daemon_{k}", val)

def create_tender(name: str) -> int:
    conn, engine = get_connection()
    c = conn.cursor()
    if engine == "postgres":
        c.execute("INSERT INTO tenders (name, status) VALUES (%s, 'PROCESANDO') RETURNING id;", (name,))
        tender_id = c.fetchone()[0]
    else:
        c.execute("INSERT INTO tenders (name, status) VALUES (?, 'PROCESANDO')", (name,))
        tender_id = c.lastrowid
    conn.commit()
    conn.close()
    return tender_id

def _rows_to_dicts(cursor, rows):
    if not rows:
        return []
    col_names = [desc[0] for desc in cursor.description]
    result = []
    for row in rows:
        d = dict(zip(col_names, row))
        # Formatear timestamps
        if 'created_at' in d and isinstance(d['created_at'], (datetime.datetime, datetime.date)):
            d['created_at'] = d['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        if 'last_scanned' in d and isinstance(d['last_scanned'], (datetime.datetime, datetime.date)):
            d['last_scanned'] = d['last_scanned'].strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return result

def get_all_tenders() -> List[Dict[str, Any]]:
    conn, engine = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tenders ORDER BY created_at DESC")
    rows = c.fetchall()
    tenders = _rows_to_dicts(c, rows)
    conn.close()
    return tenders

def get_tender(tender_id: int) -> Optional[Dict[str, Any]]:
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"SELECT * FROM tenders WHERE id = {ph}", (tender_id,))
    rows = c.fetchall()
    tenders = _rows_to_dicts(c, rows)
    conn.close()
    if tenders:
        tender = tenders[0]
        if tender.get('parsed_data'):
            try:
                pd_obj = json.loads(tender['parsed_data']) if isinstance(tender['parsed_data'], str) else tender['parsed_data']
                if "inconsistencias" not in pd_obj and "legales" in pd_obj and "contradicciones" in pd_obj["legales"]:
                    pd_obj["inconsistencias"] = [
                        {"tipo": "Contradicción", "documentos_conflicto": [], "descripcion": c}
                        for c in pd_obj["legales"]["contradicciones"]
                    ]
                if "consultas_generales" not in pd_obj and "legales" in pd_obj and "consultas_rfi" in pd_obj["legales"]:
                    pd_obj["consultas_generales"] = [
                        {"categoria": "General", "archivo_origen": "N/A", "consulta": c}
                        for c in pd_obj["legales"]["consultas_rfi"]
                    ]
                tender['parsed_data'] = pd_obj
            except Exception:
                pass
        return tender
    return None

def update_tender_status(tender_id: int, status: str, parsed_data: dict = None, error_message: str = None):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    if parsed_data is not None:
        p_json = json.dumps(parsed_data, ensure_ascii=False)
        c.execute(f"UPDATE tenders SET status = {ph}, parsed_data = {ph} WHERE id = {ph}", (status, p_json, tender_id))
    elif error_message is not None:
        c.execute(f"UPDATE tenders SET status = {ph}, error_message = {ph} WHERE id = {ph}", (status, error_message, tender_id))
    else:
        c.execute(f"UPDATE tenders SET status = {ph} WHERE id = {ph}", (status, tender_id))
    conn.commit()
    conn.close()

def update_tender_progress(tender_id: int, progress: int, msg: str):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"UPDATE tenders SET progress = {ph}, progress_msg = {ph} WHERE id = {ph}", (progress, msg, tender_id))
    conn.commit()
    conn.close()

def update_tender_parsed_data(tender_id: int, parsed_data: dict):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    p_json = json.dumps(parsed_data, ensure_ascii=False)
    c.execute(f"UPDATE tenders SET parsed_data = {ph} WHERE id = {ph}", (p_json, tender_id))
    conn.commit()
    conn.close()

def add_message(tender_id: int, role: str, content: str, chat_type: str = 'GENERAL'):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"INSERT INTO messages (tender_id, role, content, chat_type) VALUES ({ph}, {ph}, {ph}, {ph})",
              (tender_id, role, content, chat_type))
    conn.commit()
    conn.close()

def get_messages(tender_id: int, chat_type: str = 'GENERAL') -> List[Dict[str, Any]]:
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"SELECT role, content, chat_type, created_at FROM messages WHERE tender_id = {ph} AND chat_type = {ph} ORDER BY created_at ASC",
              (tender_id, chat_type))
    rows = c.fetchall()
    messages = _rows_to_dicts(c, rows)
    conn.close()
    return messages

def delete_tender(tender_id: int):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"DELETE FROM messages WHERE tender_id = {ph}", (tender_id,))
    c.execute(f"DELETE FROM tenders WHERE id = {ph}", (tender_id,))
    conn.commit()
    conn.close()

# --- Radar de Licitaciones Web ---

def get_monitored_portals() -> List[Dict[str, Any]]:
    conn, engine = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM monitored_portals ORDER BY created_at ASC")
    rows = c.fetchall()
    portals = _rows_to_dicts(c, rows)
    conn.close()
    return portals

def add_monitored_portal(name: str, url: str, frequency: str = "Diaria") -> int:
    conn, engine = get_connection()
    c = conn.cursor()
    if engine == "postgres":
        c.execute('''
            INSERT INTO monitored_portals (name, url, frequency, active)
            VALUES (%s, %s, %s, 1)
            ON CONFLICT (url) DO UPDATE SET name = EXCLUDED.name, frequency = EXCLUDED.frequency, active = 1
            RETURNING id;
        ''', (name.strip(), url.strip(), frequency))
        portal_id = c.fetchone()[0]
    else:
        c.execute("INSERT OR REPLACE INTO monitored_portals (name, url, frequency, active) VALUES (?, ?, ?, 1)",
                  (name.strip(), url.strip(), frequency))
        portal_id = c.lastrowid
    conn.commit()
    conn.close()
    return portal_id

def delete_monitored_portal(portal_id: int):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"DELETE FROM monitored_portals WHERE id = {ph}", (portal_id,))
    conn.commit()
    conn.close()

def toggle_monitored_portal(portal_id: int, active: int):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"UPDATE monitored_portals SET active = {ph} WHERE id = {ph}", (active, portal_id))
    conn.commit()
    conn.close()

def update_portal_scanned_time(portal_id: int):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"UPDATE monitored_portals SET last_scanned = CURRENT_TIMESTAMP WHERE id = {ph}", (portal_id,))
    conn.commit()
    conn.close()

def get_monitored_keywords() -> List[Dict[str, Any]]:
    conn, engine = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM monitored_keywords ORDER BY keyword ASC")
    rows = c.fetchall()
    keywords = _rows_to_dicts(c, rows)
    conn.close()
    return keywords

def add_monitored_keyword(keyword: str) -> int:
    kw = keyword.strip().lower()
    conn, engine = get_connection()
    c = conn.cursor()
    if engine == "postgres":
        c.execute('''
            INSERT INTO monitored_keywords (keyword) VALUES (%s)
            ON CONFLICT (keyword) DO NOTHING
            RETURNING id;
        ''', (kw,))
        row = c.fetchone()
        kw_id = row[0] if row else 0
    else:
        c.execute("INSERT OR IGNORE INTO monitored_keywords (keyword) VALUES (?)", (kw,))
        kw_id = c.lastrowid
    conn.commit()
    conn.close()
    return kw_id

def delete_monitored_keyword(kw_id: int):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"
    c.execute(f"DELETE FROM monitored_keywords WHERE id = {ph}", (kw_id,))
    conn.commit()
    conn.close()

def normalize_radar_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip().lower()

def normalize_radar_url(url: str) -> str:
    if not url:
        return ""
    clean = str(url).strip().rstrip('/')
    return clean.lower()

def is_opportunity_tombstoned(portal_name: str, title: str, url: str) -> bool:
    """
    Verifica si una licitación fue descartada o eliminada por el usuario,
    o si ya existe en la base de datos (evitando que el crawler vuelva a importarla).
    """
    norm_url = normalize_radar_url(url)
    norm_title = normalize_radar_text(title)
    p_norm = portal_name.strip().lower()

    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"

    # 1. Comprobar tabla radar_tombstones (por URL o por título)
    if norm_url:
        c.execute(f"SELECT id FROM radar_tombstones WHERE LOWER(url) = {ph} OR (LOWER(portal_name) = {ph} AND LOWER(title) = {ph})",
                  (norm_url, p_norm, norm_title))
    else:
        c.execute(f"SELECT id FROM radar_tombstones WHERE LOWER(portal_name) = {ph} AND LOWER(title) = {ph}",
                  (p_norm, norm_title))
    if c.fetchone():
        conn.close()
        return True

    # 2. Comprobar radar_opportunities existente
    if norm_url:
        c.execute(f"SELECT id, status FROM radar_opportunities WHERE LOWER(url) = {ph} OR (LOWER(portal_name) = {ph} AND LOWER(title) = {ph})",
                  (norm_url, p_norm, norm_title))
    else:
        c.execute(f"SELECT id, status FROM radar_opportunities WHERE LOWER(portal_name) = {ph} AND LOWER(title) = {ph}",
                  (p_norm, norm_title))
    row = c.fetchone()
    conn.close()
    if row:
        st = str(row[1] if isinstance(row, tuple) else row.get('status', '')).upper()
        # Si ya está descartada, eliminada, aprobada o pendiente, no re-importar
        return True

    return False

def save_radar_opportunity(portal_name: str, title: str, url: str, matched_keywords: str, snippet: str = "") -> int:
    clean_title = title.strip()
    clean_url = url.strip()
    if not clean_title:
        return 0

    # Si fue descartada, eliminada o ya existe, NUNCA volver a importarla
    if is_opportunity_tombstoned(portal_name, clean_title, clean_url):
        return 0

    conn, engine = get_connection()
    c = conn.cursor()
    if engine == "postgres":
        c.execute('''
            INSERT INTO radar_opportunities (portal_name, title, url, matched_keywords, snippet, status)
            VALUES (%s, %s, %s, %s, %s, 'PENDIENTE')
            ON CONFLICT (portal_name, title) DO NOTHING
            RETURNING id;
        ''', (portal_name, clean_title, clean_url, matched_keywords, snippet.strip()))
        row = c.fetchone()
        opp_id = row[0] if row else 0
    else:
        c.execute('''
            INSERT OR IGNORE INTO radar_opportunities (portal_name, title, url, matched_keywords, snippet, status)
            VALUES (?, ?, ?, ?, ?, 'PENDIENTE')
        ''', (portal_name, clean_title, clean_url, matched_keywords, snippet.strip()))
        opp_id = c.lastrowid
    conn.commit()
    conn.close()
    return opp_id

def delete_radar_opportunity(opp_id: int):
    """
    Elimina permanentemente una oportunidad del radar y la registra en radar_tombstones
    para que futuros escaneos automáticos JAMÁS la vuelvan a crear ni mostrar.
    """
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"

    c.execute(f"SELECT portal_name, title, url FROM radar_opportunities WHERE id = {ph}", (opp_id,))
    row = c.fetchone()
    if row:
        portal_name = row[0] if isinstance(row, tuple) else row.get('portal_name')
        title = row[1] if isinstance(row, tuple) else row.get('title')
        url = row[2] if isinstance(row, tuple) else row.get('url')

        if engine == "postgres":
            c.execute('''
                INSERT INTO radar_tombstones (portal_name, title, url, reason)
                VALUES (%s, %s, %s, 'ELIMINADA');
            ''', (portal_name, title, url))
        else:
            c.execute('''
                INSERT INTO radar_tombstones (portal_name, title, url, reason)
                VALUES (?, ?, ?, 'ELIMINADA');
            ''', (portal_name, title, url))

    c.execute(f"DELETE FROM radar_opportunities WHERE id = {ph}", (opp_id,))
    conn.commit()
    conn.close()

def get_pending_opportunities() -> List[Dict[str, Any]]:
    conn, engine = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM radar_opportunities WHERE status = 'PENDIENTE' ORDER BY created_at DESC")
    rows = c.fetchall()
    opps = _rows_to_dicts(c, rows)
    conn.close()
    return opps

def get_all_opportunities() -> List[Dict[str, Any]]:
    conn, engine = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM radar_opportunities WHERE status != 'ELIMINADA' ORDER BY created_at DESC")
    rows = c.fetchall()
    opps = _rows_to_dicts(c, rows)
    conn.close()
    return opps

def update_opportunity_status(opp_id: int, status: str, tender_id: int = None):
    conn, engine = get_connection()
    c = conn.cursor()
    ph = "%s" if engine == "postgres" else "?"

    clean_status = status.upper().strip()

    if clean_status in ("DESCARTADA", "ELIMINADA"):
        c.execute(f"SELECT portal_name, title, url FROM radar_opportunities WHERE id = {ph}", (opp_id,))
        row = c.fetchone()
        if row:
            portal_name = row[0] if isinstance(row, tuple) else row.get('portal_name')
            title = row[1] if isinstance(row, tuple) else row.get('title')
            url = row[2] if isinstance(row, tuple) else row.get('url')

            if engine == "postgres":
                c.execute('''
                    INSERT INTO radar_tombstones (portal_name, title, url, reason)
                    VALUES (%s, %s, %s, %s);
                ''', (portal_name, title, url, clean_status))
            else:
                c.execute('''
                    INSERT INTO radar_tombstones (portal_name, title, url, reason)
                    VALUES (?, ?, ?, ?);
                ''', (portal_name, title, url, clean_status))

    if tender_id is not None:
        c.execute(f"UPDATE radar_opportunities SET status = {ph}, tender_id = {ph} WHERE id = {ph}", (clean_status, tender_id, opp_id))
    else:
        c.execute(f"UPDATE radar_opportunities SET status = {ph} WHERE id = {ph}", (clean_status, opp_id))
    conn.commit()
    conn.close()

