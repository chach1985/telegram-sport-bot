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
LINE_ADMIN_URL = "https://lin.ee/aw2rc3s"

# --- รายชื่อกลุ่มเป้าหมาย ---
CLUB_UFA_TV = -1003749819628          
CLUB_BALLZA_TV = -1003787225016      
CLUB_PAKYOK_TV = -1003709427421      

CHANNEL_ROUTES = {
    -1003742462075: [{"group_id": CLUB_UFA_TV, "thread_id": 3, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"}],
    -1003735613798: [{"group_id": CLUB_UFA_TV, "thread_id": 3, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"}],
    -1003866345716: [{"group_id": CLUB_UFA_TV, "thread_id": 3, "type": "free"}, {"group_id": CLUB_PAKYOK_TV, "thread_id": 2, "type": "premium"}],
    -1003502971775: [{"group_id": CLUB_UFA_TV, "thread_id": 3, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"}],
    -1003898955742: [{"group_id": CLUB_UFA_TV, "thread_id": 3, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"}],
    -1003427683772: [{"group_id": CLUB_UFA_TV, "thread_id": 3, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"}],
}

# --- ระบบจัดการข้อมูลผ่าน Persistent Disk ---
DATA_FILE = os.environ.get("DATA_PATH", "/etc/data/bot_data.json")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON: {e}")
            return {"active_lives": {}, "sent_messages": {}}
    return {"active_lives": {}, "sent_messages": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving JSON: {e}")

current_data = load_data()
ACTIVE_LIVES = current_data.get("active_lives", {})
SENT_MESSAGES = current_data.get("sent_messages", {})

async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = str(update.effective_chat.id)
    if int(chat_id) in CHANNEL_ROUTES and message.video_chat_started:
        ACTIVE_LIVES[chat_id] = message.message_id
        SENT_MESSAGES[chat_id] = []
        save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})
        print(f"Live started: {chat_id}")

async def handle_live_ended(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id in ACTIVE_LIVES and update.effective_message.video_chat_ended:
        if chat_id in SENT_MESSAGES:
            # ลบเฉพาะข้อความที่เป็นประเภท premium เท่านั้น
            for msg_info in SENT_MESSAGES[chat_id]:
                if msg_info.get("type") == "premium":
                    try:
                        await context.bot.delete_message(
                            chat_id=msg_info["group_id"],
                            message_id=msg_info["message_id"]
                        )
                    except Exception as e:
                        print(f"Delete error: {e}")
            
            # ล้างข้อมูลออกจากลิสต์หลังจากจบสตรีม
            SENT_MESSAGES.pop(chat_id, None)
        
        ACTIVE_LIVES.pop(chat_id, None)
        save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})
        print(f"Live ended (Premium cleaned, Free kept): {chat_id}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if int(chat_id) not in CHANNEL_ROUTES or chat_id not in ACTIVE_LIVES:
        return
    
    live_message_id = ACTIVE_LIVES[chat_id]
    username = update.effective_chat.username
    live_link = f"https://t.me/{username}/{live_message_id}" if username else f"https://t.me/c/{chat_id[4:]}/{live_message_id}"

    ad_caption = (
        "🔴 <b>ถ่ายทอดสดเริ่มแล้ว!</b>\n"
        "อย่าพลาดความสนุก เชียร์สดไปพร้อมกันได้เลย\n\n"
        "สนใจรับชมหรือสอบถามเพิ่มเติม ติดต่อแอดมินได้ที่ปุ่มด้านล่าง 👇"
    )

    for route in CHANNEL_ROUTES[int(chat_id)]:
        try:
            sent_msg = None
            if route["type"] == "free":
                free_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("💬 ติดต่อแอดมินเพื่อรับชม", url=LINE_ADMIN_URL)]])
                sent_msg = await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=update.effective_message.photo[-1].file_id,
                    caption=ad_caption,
                    parse_mode="HTML",
                    reply_markup=free_keyboard,
                    message_thread_id=route["thread_id"],
                )
            elif route["type"] == "premium":
                premium_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=live_link)]])
                sent_msg = await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=update.effective_message.photo[-1].file_id,
                    caption="",
                    reply_markup=premium_keyboard,
                    message_thread_id=route["thread_id"],
                )
            
            # เก็บข้อมูลโดยระบุประเภท (free/premium) ไว้ด้วยเพื่อใช้กรองตอนลบ
            if sent_msg:
                SENT_MESSAGES[chat_id].append({
                    "group_id": route["group_id"], 
                    "message_id": sent_msg.message_id,
                    "type": route["type"]
                })
                save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})

        except Exception as e:
            print(f"Send error: {e}")

async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started))
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    await application.initialize()
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0", port=PORT, url_path=TOKEN,
        webhook_url=f"{WEB_URL}/{TOKEN}"
    )
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        pass
