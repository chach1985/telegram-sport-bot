import os
import asyncio
import signal
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- ข้อมูลพื้นฐาน ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
WEB_URL = "https://telegram-sport-bot-hk6a.onrender.com"

LINE_FREE_ADMIN = "https://lin.ee/aw2rc3s"
LINE_PREMIUM_ADMIN = "https://tinyurl.com/ufa345-24"
LINE_DEPOSIT_WITHDRAW = "https://lin.ee/oi2hRtr"
LOGIN_URL = "https://member.ufa345word.com/login"

CLUB_UFA_TV = -1003749819628          
CLUB_BALLZA_TV = -1003787225016      
CLUB_PAKYOK_TV = -1003709427421      

# ระบบแจ้งสตรีม (ตรวจสอบ ID แชนแนลต้นทาง)
STREAM_CHANNELS = {
    -1003742462075: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
    -1003735613798: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
    -1003866345716: [{"group_id": CLUB_UFA_TV, "thread_id": 133, "type": "free"}, {"group_id": CLUB_PAKYOK_TV, "thread_id": 1, "type": "premium"}],
    -1003502971775: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
    -1003898955742: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
    -1003427683772: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
}

DATA_PATH = os.environ.get("DATA_PATH", "/etc/data/bot_data.json")

def load_data():
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r") as f: return json.load(f)
        except: return {"active_lives": {}, "sent_messages": {}}
    return {"active_lives": {}, "sent_messages": {}}

def save_data(data):
    try:
        with open(DATA_PATH, "w") as f: json.dump(data, f)
    except: pass

db = load_data()
ACTIVE_LIVES = db.get("active_lives", {})
SENT_MESSAGES = db.get("sent_messages", {})

async def handle_stream_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if int(chat_id) not in STREAM_CHANNELS: return

    if update.effective_message.video_chat_started:
        ACTIVE_LIVES[chat_id] = update.effective_message.message_id
        SENT_MESSAGES[chat_id] = []
        save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})
    
    elif update.effective_message.video_chat_ended:
        if chat_id in ACTIVE_LIVES:
            if chat_id in SENT_MESSAGES:
                for msg in SENT_MESSAGES[chat_id]:
                    if msg.get("type") == "premium":
                        try: await context.bot.delete_message(chat_id=msg["group_id"], message_id=msg["message_id"])
                        except: pass
                SENT_MESSAGES.pop(chat_id, None)
            ACTIVE_LIVES.pop(chat_id, None)
            save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if int(chat_id) in STREAM_CHANNELS and chat_id in ACTIVE_LIVES:
        live_id = ACTIVE_LIVES[chat_id]
        user_name = update.effective_chat.username
        live_link = f"https://t.me/{user_name}/{live_id}" if user_name else f"https://t.me/c/{chat_id[4:]}/{live_id}"
        
        photo_id = update.effective_message.photo[-1].file_id

        for route in STREAM_CHANNELS[int(chat_id)]:
            kb = None
            cap = "🔴 <b>ถ่ายทอดสดเริ่มแล้ว!</b>"
            if route["type"] == "free":
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 ติดต่อแอดมินเพื่อรับชม", url=LINE_FREE_ADMIN)]])
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=live_link)],
                    [InlineKeyboardButton("📞 แอดมิน", url=LINE_PREMIUM_ADMIN), InlineKeyboardButton("💰 ฝาก-ถอน", url=LINE_DEPOSIT_WITHDRAW)],
                    [InlineKeyboardButton("🔐 เข้าสู่ระบบ", url=LOGIN_URL)]
                ])
            
            try:
                sent = await context.bot.send_photo(
                    chat_id=route["group_id"], 
                    photo=photo_id, 
                    caption=cap, 
                    parse_mode="HTML", 
                    reply_markup=kb, 
                    message_thread_id=route["thread_id"]
                )
                if chat_id not in SENT_MESSAGES: SENT_MESSAGES[chat_id] = []
                SENT_MESSAGES[chat_id].append({"group_id": route["group_id"], "message_id": sent.message_id, "type": route["type"]})
                save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})
            except: pass

async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED | filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_stream_events))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

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
