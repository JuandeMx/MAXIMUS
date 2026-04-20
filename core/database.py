import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "/etc/MaximusVpsMx/bot_data.db"

# SQL QUERIES DEFINITION (As requested)
SQL_CREATE_USERS = '''
CREATE TABLE IF NOT EXISTS telegram_users (
    user_id INTEGER PRIMARY KEY,
    last_trial TEXT,
    is_admin INTEGER DEFAULT 0,
    username_tg TEXT
)'''

SQL_CREATE_SALES = '''
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    ssh_username TEXT,
    type TEXT,
    date TEXT
)'''

def init_db():
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(SQL_CREATE_USERS)
    cursor.execute(SQL_CREATE_SALES)
    conn.commit()
    conn.close()

def get_user_status(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT last_trial, is_admin FROM telegram_users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"last_trial": row[0], "is_admin": bool(row[1])}
    return None

def update_trial(user_id, username_tg):
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO telegram_users (user_id, last_trial, username_tg) 
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET last_trial = ?, username_tg = ?
    ''', (user_id, now, username_tg, now, username_tg))
    conn.commit()
    conn.close()

def can_get_trial(user_id):
    status = get_user_status(user_id)
    if not status or not status["last_trial"]:
        return True, 0
    
    last_trial = datetime.fromisoformat(status["last_trial"])
    diff = datetime.now() - last_trial
    
    if diff >= timedelta(days=7):
        return True, 0
    
    remaining = timedelta(days=7) - diff
    return False, remaining.days
