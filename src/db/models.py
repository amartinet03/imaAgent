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
    conn.commit()
    conn.close()

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
