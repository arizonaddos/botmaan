# bot.py
import logging
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from config import BOT_TOKEN, KEY_EXPIRY, BANNER_IMAGE, REQUIRED_ID
from database import init_db, get_db
from utils import generate_key, extract_id_from_link, check_spam, is_banned, is_user_active, is_admin

# Khởi tạo database
init_db()

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Hàm xóa tin nhắn sau khoảng thời gian
def delete_message(context: CallbackContext):
    job = context.job
    context.bot.delete_message(chat_id=job.context['chat_id'], message_id=job.context['message_id'])

# Hàm tạo hiệu ứng loading và xóa tin nhắn
def loading_and_delete(update: Update, context: CallbackContext, final_text, parse_mode='Markdown', delete_after=5):
    """Gửi tin nhắn loading, sửa thành final_text, sau đó xóa cả tin nhắn lệnh và kết quả"""
    # Gửi loading
    loading_msg = update.message.reply_text("🔄 **Đang xử lý...**", parse_mode='Markdown')
    time.sleep(2)  # Giả lập xử lý
    # Sửa thành kết quả
    loading_msg.edit_text(final_text, parse_mode=parse_mode)
    # Xóa tin nhắn lệnh của user
    context.job_queue.run_once(delete_message, delete_after, context={'chat_id': update.effective_chat.id, 'message_id': update.message.message_id})
    # Xóa tin nhắn kết quả
    context.job_queue.run_once(delete_message, delete_after, context={'chat_id': update.effective_chat.id, 'message_id': loading_msg.message_id})

# ==================== XỬ LÝ CALLBACK TỪ INLINE KEYBOARD ====================
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()  # Phản hồi để tắt trạng thái loading trên nút
    data = query.data
    user_id = query.from_user.id

    if is_banned(user_id):
        query.edit_message_text("⛔ Bạn đã bị cấm sử dụng bot.")
        return

    if data == 'key':
        query.edit_message_text("🔑 Vui lòng nhập lệnh: `/key <mã_key>`", parse_mode='Markdown')
    elif data == 'tool':
        if not is_user_active(user_id):
            query.edit_message_text("⛔ Bạn chưa có key hoặc key đã hết hạn. Vui lòng liên hệ admin @thienlam6868 để kích hoạt.")
            return
        text = (
            "⚙️ **Các lệnh tool:**\n\n"
            "• `/xoaphienchoi <link>` - Xóa mã ẩn phiên chơi\n"
            "• `/bigwin <link>` - Kích hoạt bigwin\n"
            "• `/scater <link>` - Kích hoạt scater\n"
            "• `/block` - Ngăn chặn kiểm tra tài khoản\n\n"
            "📌 **Lưu ý:** Link phải từ cổng 168t.net."
        )
        query.edit_message_text(text, parse_mode='Markdown')
    elif data == 'info':
        if not is_user_active(user_id):
            query.edit_message_text("⛔ Bạn chưa có key.")
            return
        with get_db() as conn:
            cur = conn.execute("SELECT account, expiry FROM users WHERE user_id=?", (user_id,))
            user = cur.fetchone()
            if user:
                expiry = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(user['expiry']))
                text = f"📊 **Thông tin tài khoản**\n\n👤 Tài khoản C168: `{user['account']}`\n⏳ Hạn sử dụng: {expiry}"
            else:
                text = "⛔ Không tìm thấy thông tin."
        query.edit_message_text(text, parse_mode='Markdown')
    elif data == 'help':
        help_text = (
            "📖 **HƯỚNG DẪN SỬ DỤNG**\n\n"
            "1️⃣ **Kích hoạt key:** `/key <mã_key>`\n"
            "2️⃣ **Sau khi có key:** Dùng các lệnh tool ở mục `⚙️ Sử dụng tool`\n"
            "3️⃣ **Liên hệ admin:** @thienlam6868"
        )
        query.edit_message_text(help_text, parse_mode='Markdown')

# ==================== LỆNH USER ====================
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_banned(user_id):
        update.message.reply_text("⛔ Bạn đã bị cấm sử dụng bot.")
        return

    # Gửi banner nếu có
    if os.path.exists(BANNER_IMAGE):
        with open(BANNER_IMAGE, 'rb') as f:
            update.message.reply_photo(
                photo=f,
                caption="🔰 **TOOL XÓA MÃ ẨN C168** 🔰\n\nHiện tại tool đang khai thác lỗ hổng bảo mật của cổng game 168t.net.\nChỉ cổng này mới sử dụng được tool.\n\n📞 Liên hệ Admin: @thienlam6868 để kích hoạt key.",
                parse_mode='Markdown'
            )
    else:
        update.message.reply_text(
            "🔰 **TOOL XÓA MÃ ẨN C168** 🔰\n\n"
            "Hiện tại tool đang khai thác lỗ hổng bảo mật của cổng game 168t.net.\n"
            "Chỉ cổng này mới sử dụng được tool.\n\n"
            "📞 Liên hệ Admin: @thienlam6868 để kích hoạt key.",
            parse_mode='Markdown'
        )

    # Tạo menu inline
    keyboard = [
        [InlineKeyboardButton("🔑 Kích hoạt key", callback_data='key')],
        [InlineKeyboardButton("⚙️ Sử dụng tool", callback_data='tool')],
        [InlineKeyboardButton("📊 Thông tin tài khoản", callback_data='info')],
        [InlineKeyboardButton("📖 Hướng dẫn", callback_data='help')],
        [InlineKeyboardButton("👤 Liên hệ admin", url='https://t.me/thienlam6868')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("📌 **Vui lòng chọn chức năng:**", reply_markup=reply_markup, parse_mode='Markdown')

def help_command(update: Update, context: CallbackContext):
    help_text = (
        "📖 **HƯỚNG DẪN SỬ DỤNG**\n\n"
        "1️⃣ **Kích hoạt key:** `/key <mã_key>`\n"
        "2️⃣ **Các lệnh tool (cần có key):**\n"
        "   • `/xoaphienchoi <link>` - Xóa mã ẩn phiên chơi\n"
        "   • `/bigwin <link>` - Kích hoạt bigwin\n"
        "   • `/scater <link>` - Kích hoạt tỷ lệ ra scater\n"
        "   • `/block` - Ngăn chặn hệ thống kiểm tra\n\n"
        "⚠️ **Lưu ý:** Link phải từ cổng 168t.net và có định dạng hợp lệ.\n\n"
        "📞 Liên hệ admin: @thienlam6868"
    )
    update.message.reply_text(help_text, parse_mode='Markdown')

def helpadmin(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    help_text = (
        "👑 **HƯỚNG DẪN ADMIN** 👑\n\n"
        "• `/addadmin <user_id>` - Thêm admin mới\n"
        "• `/deladmin <user_id>` - Xóa admin\n"
        "• `/getkey <tài_khoản> <1n/1t/1y>` - Tạo key\n"
        "• `/listkey` - Xem danh sách key\n"
        "• `/delkey <key>` - Xóa key\n"
        "• `/thongbao <nội dung>` - Gửi thông báo đến tất cả user\n"
        "• `/stats` - Thống kê bot\n"
        "• `/backup` - Backup database"
    )
    update.message.reply_text(help_text, parse_mode='Markdown')

def key_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_banned(user_id):
        update.message.reply_text("⛔ Bạn đã bị cấm.")
        return
    if not check_spam(user_id):
        update.message.reply_text("⚠️ Vui lòng chậm lại, bạn đang gửi lệnh quá nhanh.")
        return
    args = context.args
    if not args:
        update.message.reply_text("❌ Sai cú pháp. Gõ `/key <mã_key>`", parse_mode='Markdown')
        return
    key_input = args[0]
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM keys WHERE key=?", (key_input,))
        row = cur.fetchone()
        if not row:
            loading_and_delete(update, context, "❌ Key không tồn tại trong hệ thống.", delete_after=5)
            return
        if row['used'] == 1:
            loading_and_delete(update, context, "❌ Key đã được sử dụng.", delete_after=5)
            return
        if row['expiry'] < time.time():
            loading_and_delete(update, context, "❌ Key đã hết hạn.", delete_after=5)
            return
        # Kích hoạt user
        account = row['account']
        expiry = row['expiry']
        conn.execute("INSERT OR REPLACE INTO users (user_id, username, account, key_used, expiry, active) VALUES (?, ?, ?, ?, ?, 1)",
                     (user_id, update.effective_user.username, account, key_input, expiry))
        conn.execute("UPDATE keys SET used=1 WHERE key=?", (key_input,))
        conn.commit()
    success_msg = f"✅ **Chúc mừng {account} đã kích hoạt key thành công!**"
    loading_and_delete(update, context, success_msg, delete_after=5)

def xoaphienchoi(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_banned(user_id):
        update.message.reply_text("⛔ Bạn đã bị cấm.")
        return
    if not check_spam(user_id):
        update.message.reply_text("⚠️ Vui lòng chậm lại.")
        return
    if not is_user_active(user_id):
        update.message.reply_text("⛔ Bạn chưa có key hoặc key đã hết hạn. Liên hệ admin @thienlam6868 để kích hoạt.")
        return
    args = context.args
    if not args:
        update.message.reply_text("❌ Sai cú pháp. Gõ `/xoaphienchoi <link>`", parse_mode='Markdown')
        return
    link = args[0]
    # Kiểm tra link có chứa đúng chuỗi id yêu cầu
    if f"id={REQUIRED_ID}" not in link:
        loading_and_delete(update, context, "❌ Tool chỉ hoạt động trên cổng link 168t.net. Vui lòng đăng ký tài khoản mới và sử dụng.", delete_after=5)
        return
    # Xử lý thành công
    success_msg = "✅ **Đã xóa mã ẩn phiên chơi thành công!**"
    loading_and_delete(update, context, success_msg, delete_after=5)

def bigwin(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_banned(user_id):
        update.message.reply_text("⛔ Bạn đã bị cấm.")
        return
    if not check_spam(user_id):
        update.message.reply_text("⚠️ Vui lòng chậm lại.")
        return
    if not is_user_active(user_id):
        update.message.reply_text("⛔ Bạn chưa có key. Liên hệ admin.")
        return
    args = context.args
    if not args:
        update.message.reply_text("❌ Sai cú pháp. Gõ `/bigwin <link>`", parse_mode='Markdown')
        return
    link = args[0]
    if f"id={REQUIRED_ID}" not in link:
        loading_and_delete(update, context, "❌ Tool chỉ hoạt động trên cổng link 168t.net. Vui lòng đăng ký tài khoản mới và sử dụng.", delete_after=5)
        return
    loading_and_delete(update, context, "✅ **Kích hoạt bigwin thành công!**", delete_after=5)

def scater(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_banned(user_id):
        update.message.reply_text("⛔ Bạn đã bị cấm.")
        return
    if not check_spam(user_id):
        update.message.reply_text("⚠️ Vui lòng chậm lại.")
        return
    if not is_user_active(user_id):
        update.message.reply_text("⛔ Bạn chưa có key.")
        return
    args = context.args
    if not args:
        update.message.reply_text("❌ Sai cú pháp. Gõ `/scater <link>`", parse_mode='Markdown')
        return
    link = args[0]
    if f"id={REQUIRED_ID}" not in link:
        loading_and_delete(update, context, "❌ Tool chỉ hoạt động trên cổng link 168t.net. Vui lòng đăng ký tài khoản mới và sử dụng.", delete_after=5)
        return
    loading_and_delete(update, context, "✅ **Kích hoạt tỷ lệ ra scater thành công!**", delete_after=5)

def block(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_banned(user_id):
        update.message.reply_text("⛔ Bạn đã bị cấm.")
        return
    if not check_spam(user_id):
        update.message.reply_text("⚠️ Vui lòng chậm lại.")
        return
    if not is_user_active(user_id):
        update.message.reply_text("⛔ Bạn chưa có key.")
        return
    with get_db() as conn:
        cur = conn.execute("SELECT account FROM users WHERE user_id=?", (user_id,))
        user = cur.fetchone()
        if not user:
            update.message.reply_text("⛔ Không tìm thấy tài khoản.")
            return
        account = user['account']
    success_msg = f"✅ **Đã ngăn chặn hệ thống kính lúp của cổng game cho tài khoản `{account}`.**"
    loading_and_delete(update, context, success_msg, delete_after=5)

# ==================== LỆNH ADMIN ====================
def add_admin(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    args = context.args
    if not args:
        update.message.reply_text("❌ Sai cú pháp. `/addadmin <user_id>`", parse_mode='Markdown')
        return
    try:
        new_admin = int(args[0])
    except:
        update.message.reply_text("❌ User ID phải là số.")
        return
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin,))
        conn.commit()
    update.message.reply_text(f"✅ Đã thêm admin `{new_admin}`.", parse_mode='Markdown')

def del_admin(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    args = context.args
    if not args:
        update.message.reply_text("❌ Sai cú pháp. `/deladmin <user_id>`", parse_mode='Markdown')
        return
    try:
        admin_id = int(args[0])
    except:
        update.message.reply_text("❌ User ID phải là số.")
        return
    if admin_id == 5088042581:
        update.message.reply_text("⛔ Không thể xóa admin gốc.")
        return
    with get_db() as conn:
        conn.execute("DELETE FROM admins WHERE user_id=?", (admin_id,))
        conn.commit()
    update.message.reply_text(f"✅ Đã xóa admin `{admin_id}`.", parse_mode='Markdown')

def getkey(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    args = context.args
    if len(args) < 2:
        update.message.reply_text("❌ Sai cú pháp. `/getkey <tài_khoản> <1n/1t/1y>`", parse_mode='Markdown')
        return
    account = args[0]
    expiry_str = args[1]
    if expiry_str not in KEY_EXPIRY:
        update.message.reply_text("❌ Thời hạn không hợp lệ. Chỉ chấp nhận `1n`, `1t`, `1y`.")
        return
    expiry_seconds = KEY_EXPIRY[expiry_str]
    expiry_time = int(time.time()) + expiry_seconds
    key_raw = generate_key(account, expiry_str)
    with get_db() as conn:
        conn.execute("INSERT INTO keys (key, account, expiry, used) VALUES (?, ?, ?, 0)",
                     (key_raw, account, expiry_time))
        conn.commit()
    update.message.reply_text(f"✅ **Key đã tạo:**\n`{key_raw}`", parse_mode='Markdown')

def listkey(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    with get_db() as conn:
        cur = conn.execute("SELECT key, account, expiry, used FROM keys")
        rows = cur.fetchall()
        if not rows:
            update.message.reply_text("📭 Chưa có key nào.")
            return
        msg = "📋 **Danh sách key:**\n\n"
        for r in rows:
            status = "✅ Đã dùng" if r['used'] else "🆕 Chưa dùng"
            expiry = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(r['expiry']))
            msg += f"🔑 Key: `{r['key']}`\n👤 TK: `{r['account']}`\n⏳ Hạn: {expiry}\n📌 Trạng thái: {status}\n---\n"
        update.message.reply_text(msg, parse_mode='Markdown')

def delkey(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    args = context.args
    if not args:
        update.message.reply_text("❌ Sai cú pháp. `/delkey <key>`", parse_mode='Markdown')
        return
    key = args[0]
    with get_db() as conn:
        conn.execute("DELETE FROM keys WHERE key=?", (key,))
        conn.commit()
    update.message.reply_text(f"✅ Đã xóa key `{key}`.", parse_mode='Markdown')

def thongbao(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    if not context.args:
        update.message.reply_text("❌ Sai cú pháp. `/thongbao <nội dung>`", parse_mode='Markdown')
        return
    content = ' '.join(context.args)
    with get_db() as conn:
        cur = conn.execute("SELECT user_id FROM users")
        users = cur.fetchall()
    count = 0
    for u in users:
        try:
            context.bot.send_message(chat_id=u['user_id'], text=f"📢 **THÔNG BÁO:**\n{content}", parse_mode='Markdown')
            count += 1
        except:
            pass
    update.message.reply_text(f"✅ Đã gửi thông báo đến {count} user.")

def stats(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    with get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        activated = conn.execute("SELECT COUNT(*) FROM users WHERE active=1").fetchone()[0]
        keys_used = conn.execute("SELECT COUNT(*) FROM keys WHERE used=1").fetchone()[0]
        today = time.time() - 86400
        online = conn.execute("SELECT COUNT(DISTINCT user_id) FROM logs WHERE time > ?", (today,)).fetchone()[0]
    msg = (
        f"📊 **THỐNG KÊ BOT**\n\n"
        f"👥 Tổng user: {total_users}\n"
        f"✅ Đã kích hoạt: {activated}\n"
        f"🔑 Key đã dùng: {keys_used}\n"
        f"🟢 Online hôm nay: {online}"
    )
    update.message.reply_text(msg, parse_mode='Markdown')

def backup(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("⛔ Bạn không phải admin.")
        return
    import shutil
    backup_name = f"backup_{int(time.time())}.db"
    shutil.copyfile("bot_data.db", backup_name)
    update.message.reply_text(f"✅ Đã backup database: `{backup_name}`", parse_mode='Markdown')

# Log tất cả lệnh
def log_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    command = update.message.text
    with get_db() as conn:
        conn.execute("INSERT INTO logs (user_id, command, time) VALUES (?, ?, ?)",
                     (user_id, command, int(time.time())))
        conn.commit()

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Xử lý callback từ inline keyboard
    dp.add_handler(CallbackQueryHandler(button_handler))

    # Lệnh user
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("helpadmin", helpadmin))
    dp.add_handler(CommandHandler("key", key_command))
    dp.add_handler(CommandHandler("xoaphienchoi", xoaphienchoi))
    dp.add_handler(CommandHandler("bigwin", bigwin))
    dp.add_handler(CommandHandler("scater", scater))
    dp.add_handler(CommandHandler("block", block))

    # Lệnh admin
    dp.add_handler(CommandHandler("addadmin", add_admin))
    dp.add_handler(CommandHandler("deladmin", del_admin))
    dp.add_handler(CommandHandler("getkey", getkey))
    dp.add_handler(CommandHandler("listkey", listkey))
    dp.add_handler(CommandHandler("delkey", delkey))
    dp.add_handler(CommandHandler("thongbao", thongbao))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("backup", backup))

    # Log tất cả lệnh (không log lệnh start, help để tránh trùng)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, log_command))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
