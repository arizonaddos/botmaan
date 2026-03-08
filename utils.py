# utils.py
import random
import string
import time
import re
from database import get_db

def generate_key(account, expiry_str):
    """Tạo key ngẫu nhiên chứa account và thời hạn"""
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"{random_part}{account}{random_part}{expiry_str}{random_part}"

def extract_id_from_link(link):
    """Trích xuất giá trị id từ link (nếu có)"""
    match = re.search(r'id=(\d+)', link)
    return match.group(1) if match else None

def check_spam(user_id):
    """Kiểm tra spam: cách 10 giây mới được gửi lệnh tiếp"""
    last_time = {}
    now = time.time()
    if user_id in last_time and now - last_time[user_id] < 10:
        return False
    last_time[user_id] = now
    return True

def is_banned(user_id):
    """Kiểm tra user có bị cấm không"""
    with get_db() as conn:
        cur = conn.execute("SELECT 1 FROM banned WHERE user_id=?", (user_id,))
        return cur.fetchone() is not None

def is_user_active(user_id):
    """Kiểm tra user có key còn hạn không"""
    with get_db() as conn:
        cur = conn.execute("SELECT active, expiry FROM users WHERE user_id=?", (user_id,))
        user = cur.fetchone()
        if not user or user['active'] == 0:
            return False
        if user['expiry'] < time.time():
            conn.execute("UPDATE users SET active=0 WHERE user_id=?", (user_id,))
            conn.commit()
            return False
        return True

def is_admin(user_id):
    """Kiểm tra quyền admin"""
    with get_db() as conn:
        cur = conn.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
        return cur.fetchone() is not None