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
ADMIN_IDS = [7029914099, 5915826734, 7945628926, 6942060939] 

# ลิงก์ปุ่มต่างๆ
LINE_FREE_ADMIN = "https://lin.ee/aw2rc3s"
LINE_PREMIUM_ADMIN = "https://tinyurl.com/ufa345-24"
LINE_DEPOSIT_WITHDRAW = "https://lin.ee/oi2hRtr"
LOGIN_URL = "https://member.ufa345word.com/login"

# --- รายชื่อกลุ่มและ Topic ---
CLUB_UFA_TV = -1003749819628          
CLUB_BALLZA_TV = -1003787225016      
CLUB_PAKYOK_TV = -1003709427421      

# เส้นทางสำหรับแอดมินส่งข่าว (Broadcast)
ROUTES = {
    "ufa_ball": {"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free", "name": "CLUB UFA (บอล)"},
    "ufa_muay": {"group_id": CLUB_UFA_TV, "thread_id": 133, "type": "free", "name": "CLUB UFA (มวย)"},
    "ballza":   {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium", "name": "CLUB BALLZA"},
    "pakyok":   {"group_id": CLUB_PAKYOK_TV, "thread_id": 1, "type": "premium", "name": "CLUB PAKYOK"},
}

# เส้นทางสำหรับระบบแจ้งสตรีม (Live Stream Detection)
STREAM_CHANNELS = {
    -1003742462075: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
    -1003735613798: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
    -1003866345716: [{"group_id": CLUB_UFA_TV, "thread_id": 133, "type": "free"}, {"group_id": CLUB_PAKYOK_TV, "thread_id": 1, "type": "premium"}],
    -1003502971775: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
    -1003898955742: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
    -1003427683772: [{"group_id": CLUB_UFA_TV, "thread_id": 129, "type": "free"}, {"group_id": CLUB_BALLZA_TV, "thread_id": 1, "type": "premium"}],
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

# --- 1. ระบบแจ้งสตรีม (อัตโนมัติ) ---
async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if int(chat_id) in STREAM_CHANNELS and update.effective_message.video_chat_started:
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

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    # ถ้าเป็นรูปจากแชนแนลสตรีม และมีการเปิดสตรีมอยู่
    if int(chat_id) in STREAM_CHANNELS and chat_id in ACTIVE_LIVES:
        live_id = ACTIVE_LIVES[chat_id]
        user_name = update.effective_chat.username
        live_link = f"https://t.me/{user_name}/{live_id}" if user_name else f"https://t.me/c/{chat_id[4:]}/{live_id}"
        
        for route in STREAM_CHANNELS[int(chat_id)]:
            kb = None
            cap = update.effective_message.caption or ""
            if route["type"] == "free":
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 ติดต่อแอดมินเพื่อรับชม", url=LINE_FREE_ADMIN)]])
                cap = "🔴 <b>ถ่ายทอดสดเริ่มแล้ว!</b>\nสนใจรับชมติดต่อแอดมินครับ 👇"
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=live_link)],
                    [InlineKeyboardButton("📞 แอดมิน", url=LINE_PREMIUM_ADMIN), InlineKeyboardButton("💰 ฝาก-ถอน", url=LINE_DEPOSIT_WITHDRAW)],
                    [InlineKeyboardButton("🔐 เข้าสู่ระบบ", url=LOGIN_URL)]
                ])
            
            try:
                sent = await context.bot.send_photo(chat_id=route["group_id"], photo=update.effective_message.photo[-1].file_id, 
                                                   caption=cap, parse_mode="HTML", reply_markup=kb, message_thread_id=route["thread_id"])
                SENT_MESSAGES[chat_id].append({"group_id": route["group_id"], "message_id": sent.message_id, "type": route["type"]})
                save_data({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES})
            except: pass

# --- 2. ระบบแอดมินส่งข่าว (Broadcast) ---
async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    keyboard = [[InlineKeyboardButton(f"📤 ส่งไป: {info['name']}", callback_data=f"target_{key}")] for key, info in ROUTES.items()]
    await update.message.reply_text("🛠 **Admin Control Panel**\nเลือกกลุ่มเป้าหมาย:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS: return
    await query.answer()
    
    if query.data.startswith("target_"):
        context.user_data['target'] = query.data.replace("target_", "")
        kb = [[InlineKeyboardButton("✅ ใช่ (มีปุ่มลิงก์)", callback_data="mode_with_kb")],
              [InlineKeyboardButton("❌ ไม่ (เฉพาะเนื้อหา)", callback_data="mode_no_kb")]]
        await query.edit_message_text(f"กลุ่ม: **{ROUTES[context.user_data['target']]['name']}**\n\nต้องการปุ่มลิงก์หรือไม่?", reply_markup=InlineKeyboardMarkup(kb))
    
    elif query.data.startswith("mode_"):
        context.user_data['mode'] = query.data.replace("mode_", "")
        await query.edit_message_text(f"ตั้งค่าเรียบร้อย! ✅\n📌 **ส่งรูปหรือข้อความมาได้เลยครับ**")

async def handle_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ตรวจสอบว่าเป็นแอดมิน และไม่ได้มาจากแชนแนลสตรีม (เพื่อแยกกับ handle_photo)
    if update.effective_user.id not in ADMIN_IDS or 'target' not in context.user_data: return
    if update.effective_chat.type != "private": return

    target = ROUTES[context.user_data['target']]
    mode = context.user_data.get('mode', 'with_kb')
    kb = None
    cap = update.effective_message.caption or ""

    if mode == "with_kb":
        if target["type"] == "free":
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 ติดต่อแอดมิน", url=LINE_FREE_ADMIN)]])
            cap += "\n\nสนใจรับชมติดต่อแอดมินครับ"
        else:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=LOGIN_URL)],
                [InlineKeyboardButton("📞 แอดมิน", url=LINE_PREMIUM_ADMIN), InlineKeyboardButton("💰 ฝาก-ถอน", url=LINE_DEPOSIT_WITHDRAW)],
                [InlineKeyboardButton("🔐 เข้าสู่ระบบ", url=LOGIN_URL)]
            ])

    try:
        if update.effective_message.photo:
            await context.bot.send_photo(chat_id=target["group_id"], photo=update.effective_message.photo[-1].file_id, 
                                       caption=cap, parse_mode="HTML", reply_markup=kb, message_thread_id=target["thread_id"])
        else:
            await context.bot.send_message(chat_id=target["group_id"], text=update.effective_message.text, 
                                         reply_markup=kb, message_thread_id=target["thread_id"], parse_mode="HTML")
        await update.message.reply_text("✅ ส่งเรียบร้อย!")
        context.user_data.clear()
    except Exception as e: await update.message.reply_text(f"❌ ผิดพลาด: {e}")

# --- รันบอท ---
async def run_bot():
    application = Application.builder().token(TOKEN).build()
    # แอดมิน
    application.add_handler(CommandHandler("start", start_admin))
    application.add_handler(CallbackQueryHandler(button_callback))
    # แจ้งสตรีม
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started))
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended))
    # จัดการรูปภาพ (แยกสตรีมกับแอดมิน)
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & (~filters.COMMAND), handle_photo), group=1)
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & (~filters.COMMAND), handle_broadcast_input), group=2)

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
