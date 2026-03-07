import os
import asyncio
import signal
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    CommandHandler,
)

# --- ข้อมูลพื้นฐานจากที่คุณให้มา ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
WEB_URL = "https://telegram-sport-bot-hk6a.onrender.com"
ADMIN_IDS = [7029914099, 5915826734] # ID ของคุณและทีมงาน

# ลิงก์ปุ่มต่างๆ
LINE_FREE_ADMIN = "https://lin.ee/aw2rc3s"
LINE_PREMIUM_ADMIN = "https://tinyurl.com/ufa345-24"
LINE_DEPOSIT_WITHDRAW = "https://lin.ee/oi2hRtr"
LOGIN_URL = "https://member.ufa345word.com/login"

# --- รายชื่อกลุ่มและ Topic ---
CLUB_UFA_TV = -1003749819628          
CLUB_BALLZA_TV = -1003787225016      
CLUB_PAKYOK_TV = -1003709427421      

# เส้นทางส่งข้อความ
ROUTES = {
    "ufa_ball": {"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free", "name": "CLUB UFA (บอล)"},
    "ufa_muay": {"group_id": CLUB_UFA_TV, "thread_id": 133, "type": "free", "name": "CLUB UFA (มวย)"},
    "ballza":   {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium", "name": "CLUB BALLZA"},
    "pakyok":   {"group_id": CLUB_PAKYOK_TV, "thread_id": 1, "type": "premium", "name": "CLUB PAKYOK"},
}

DATA_FILE = os.environ.get("DATA_PATH", "/etc/data/bot_data.json")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {"active_lives": {}, "sent_messages": {}, "admin_states": {}}
    return {"active_lives": {}, "sent_messages": {}, "admin_states": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

current_data = load_data()
ACTIVE_LIVES = current_data.get("active_lives", {})
SENT_MESSAGES = current_data.get("sent_messages", {})

# --- ฟังก์ชันสำหรับ Admin Panel ---
async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    
    keyboard = []
    for key, info in ROUTES.items():
        keyboard.append([InlineKeyboardButton(f"📤 ส่งไป: {info['name']}", callback_data=f"target_{key}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠 **Admin Control**\nเลือกกลุ่มที่ต้องการกระจายข่าว:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS: return
    await query.answer()

    if query.data.startswith("target_"):
        target_key = query.data.replace("target_", "")
        context.user_data['broadcast_target'] = target_key
        await query.edit_message_text(f"✅ เลือกกลุ่ม: **{ROUTES[target_key]['name']}**\n\n📌 **กรุณาส่งรูปภาพ หรือ พิมพ์ข้อความที่ต้องการส่งได้เลยครับ**")

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS or 'broadcast_target' not in context.user_data:
        return

    target_key = context.user_data['broadcast_target']
    route = ROUTES[target_key]
    
    # เตรียมปุ่มตามประเภทกลุ่ม
    if route["type"] == "free":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("💬 ติดต่อแอดมิน", url=LINE_FREE_ADMIN)]])
        caption = f"{update.effective_message.caption}\n\n" if update.effective_message.caption else ""
        caption += "สนใจรับชมติดต่อแอดมินได้เลยครับ 👇"
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=LOGIN_URL)], # ใส่ลิงก์เริ่มต้น
            [InlineKeyboardButton("📞 ติดต่อแอดมิน", url=LINE_PREMIUM_ADMIN), InlineKeyboardButton("💰 ฝาก-ถอน", url=LINE_DEPOSIT_WITHDRAW)],
            [InlineKeyboardButton("🔐 เข้าสู่ระบบ", url=LOGIN_URL)]
        ])
        caption = update.effective_message.caption or ""

    try:
        if update.effective_message.photo:
            await context.bot.send_photo(
                chat_id=route["group_id"],
                photo=update.effective_message.photo[-1].file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
                message_thread_id=route["thread_id"]
            )
        else:
            await context.bot.send_message(
                chat_id=route["group_id"],
                text=update.effective_message.text,
                reply_markup=keyboard,
                message_thread_id=route["thread_id"]
            )
        await update.message.reply_text("✅ **กระจายข้อความเรียบร้อย!**")
        del context.user_data['broadcast_target']
    except Exception as e:
        await update.message.reply_text(f"❌ เกิดข้อผิดพลาด: {e}")

# --- (ฟังก์ชัน Live Streaming เหมือนเดิมคงไว้) ---
# ... (ส่วน handle_live_started, handle_live_ended, handle_photo จากโค้ดก่อนหน้า)

async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_admin))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & (~filters.COMMAND), handle_broadcast))
    # handlers สำหรับสตรีม
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started))
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended))
    
    await application.initialize()
    await application.start()
    await application.updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=f"{WEB_URL}/{TOKEN}")
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM): loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    try: asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit): pass
