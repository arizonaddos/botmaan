# database.py
import sqlite3
from config import DATABASE, ADMIN_IDS

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Bảng users
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            account TEXT,
            key_used TEXT,
            expiry INTEGER,
            active INTEGER DEFAULT 0
        )''')
        # Bảng keys
        conn.execute('''CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            account TEXT,
            expiry INTEGER,
            used INTEGER DEFAULT 0
        )''')
        # Bảng admins
        conn.execute('''CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )''')
        # Bảng logs
        conn.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            command TEXT,
            time INTEGER
        )''')
        # Bảng banned
        conn.execute('''CREATE TABLE IF NOT EXISTS banned (
            user_id INTEGER PRIMARY KEY
        )''')
        # Thêm admin mặc định
        for uid in ADMIN_IDS:
            conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))