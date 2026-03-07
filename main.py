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

# --- ข้อมูลพื้นฐาน ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
WEB_URL = "https://telegram-sport-bot-hk6a.onrender.com"

# อัปเดตรายชื่อ ADMIN_IDS (เพิ่ม ID ใหม่เรียบร้อย)
ADMIN_IDS = [7029914099, 5915826734, 7945628926] 

# ลิงก์ปุ่มต่างๆ (ใช้ค่าเดิมที่คุณตั้งไว้)
LINE_FREE_ADMIN = "https://lin.ee/aw2rc3s"
LINE_PREMIUM_ADMIN = "https://tinyurl.com/ufa345-24"
LINE_DEPOSIT_WITHDRAW = "https://lin.ee/oi2hRtr"
LOGIN_URL = "https://member.ufa345word.com/login"

# --- การตั้งค่ากลุ่มและ Topic ---
CLUB_UFA_TV = -1003749819628          
CLUB_BALLZA_TV = -1003787225016      
CLUB_PAKYOK_TV = -1003709427421      

ROUTES = {
    "ufa_ball": {"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free", "name": "CLUB UFA (บอล)"},
    "ufa_muay": {"group_id": CLUB_UFA_TV, "thread_id": 133, "type": "free", "name": "CLUB UFA (มวย)"},
    "ballza":   {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium", "name": "CLUB BALLZA"},
    "pakyok":   {"group_id": CLUB_PAKYOK_TV, "thread_id": 1, "type": "premium", "name": "CLUB PAKYOK"},
}

DATA_PATH = os.environ.get("DATA_PATH", "/etc/data/bot_data.json")

# --- ฟังก์ชันจัดการข้อมูล ---
def load_data():
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r") as f: return json.load(f)
        except: return {"active_lives": {}, "sent_messages": {}}
    return {"active_lives": {}, "sent_messages": {}}

def save_data(data):
    try:
        with open(DATA_PATH, "w") as f: json.dump(data, f)
    except Exception as e: print(f"Save error: {e}")

db = load_data()
ACTIVE_LIVES = db.get("active_lives", {})
SENT_MESSAGES = db.get("sent_messages", {})

# --- ส่วน Admin Control Panel ---
async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    keyboard = [[InlineKeyboardButton(f"📤 ส่งไป: {info['name']}", callback_data=f"target_{key}")] for key, info in ROUTES.items()]
    await update.message.reply_text("🛠 **Admin Control Panel**\nแอดมินเลือกกลุ่มที่ต้องการส่งข่าวสาร:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS: return
    await query.answer()
    target_key = query.data.replace("target_", "")
    context.user_data['broadcast_target'] = target_key
    await query.edit_message_text(f"✅ เลือกกลุ่ม: **{ROUTES[target_key]['name']}**\n📌 ส่งรูปหรือข้อความที่ต้องการกระจายข่าวมาได้เลยครับ")

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS or 'broadcast_target' not in context.user_data: return
    target_key = context.user_data['broadcast_target']
    route = ROUTES[target_key]
    
    if route["type"] == "free":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 ติดต่อแอดมิน", url=LINE_FREE_ADMIN)]])
        cap = f"{update.effective_message.caption}\n\nสนใจรับชมติดต่อแอดมินครับ" if update.effective_message.caption else "สนใจรับชมติดต่อแอดมินครับ"
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=LOGIN_URL)],
            [InlineKeyboardButton("📞 แอดมิน", url=LINE_PREMIUM_ADMIN), InlineKeyboardButton("💰 ฝาก-ถอน", url=LINE_DEPOSIT_WITHDRAW)],
            [InlineKeyboardButton("🔐 เข้าสู่ระบบ", url=LOGIN_URL)]
        ])
        cap = update.effective_message.caption or ""

    if update.effective_message.photo:
        await context.bot.send_photo(chat_id=route["group_id"], photo=update.effective_message.photo[-1].file_id, caption=cap, parse_mode="HTML", reply_markup=kb, message_thread_id=route["thread_id"])
    else:
        await context.bot.send_message(chat_id=route["group_id"], text=update.effective_message.text, reply_markup=kb, message_thread_id=route["thread_id"])
    
    await update.message.reply_text("✅ กระจายข้อความไปยังกลุ่มเป้าหมายเรียบร้อย!")
    del context.user_data['broadcast_target']

# --- ส่วน Live Streaming ---
async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if update.effective_message.video_chat_started:
        ACTIVE_LIVES[chat_id] = update.effective_message.message_id
        SENT_MESSAGES[chat_id] = []
        save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})

async def handle_live_ended(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id in ACTIVE_LIVES and update.effective_message.video_chat_ended:
        if chat_id in SENT_MESSAGES:
            for msg in SENT_MESSAGES[chat_id]:
                if msg.get("type") == "premium":
                    try: await context.bot.delete_message(chat_id=msg["group_id"], message_id=msg["message_id"])
                    except: pass
            SENT_MESSAGES.pop(chat_id, None)
        ACTIVE_LIVES.pop(chat_id, None)
        save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})

# --- เริ่มการทำงานของบอท ---
async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_admin))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started))
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended))
    application.add_handler(MessageHandler((filters.PHOTO | filters.TEXT) & (~filters.COMMAND), handle_broadcast))

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
