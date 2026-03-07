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
ADMIN_IDS = [7029914099, 5915826734, 7945628926] 

LINE_FREE_ADMIN = "https://lin.ee/aw2rc3s"
LINE_PREMIUM_ADMIN = "https://tinyurl.com/ufa345-24"
LINE_DEPOSIT_WITHDRAW = "https://lin.ee/oi2hRtr"
LOGIN_URL = "https://member.ufa345word.com/login"

ROUTES = {
    "ufa_ball": {"group_id": -1003749819628, "thread_id": 129, "type": "free", "name": "CLUB UFA (บอล)"},
    "ufa_muay": {"group_id": -1003749819628, "thread_id": 133, "type": "free", "name": "CLUB UFA (มวย)"},
    "ballza":   {"group_id": -1003787225016, "thread_id": 1, "type": "premium", "name": "CLUB BALLZA"},
    "pakyok":   {"group_id": -1003709427421, "thread_id": 1, "type": "premium", "name": "CLUB PAKYOK"},
}

DATA_PATH = os.environ.get("DATA_PATH", "/etc/data/bot_data.json")

# --- ฟังก์ชันจัดการแอดมิน ---
async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    keyboard = [[InlineKeyboardButton(f"📤 ส่งไป: {info['name']}", callback_data=f"target_{key}")] for key, info in ROUTES.items()]
    await update.message.reply_text("🛠 **Admin Control Panel**\nเลือกกลุ่มเป้าหมาย:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS: return
    await query.answer()
    
    data = query.data
    if data.startswith("target_"):
        context.user_data['target'] = data.replace("target_", "")
        kb = [
            [InlineKeyboardButton("✅ ใช่ (มีปุ่มลิงก์)", callback_data="mode_with_kb")],
            [InlineKeyboardButton("❌ ไม่ (เฉพาะเนื้อหา)", callback_data="mode_no_kb")]
        ]
        await query.edit_message_text(f"กลุ่มที่เลือก: **{ROUTES[context.user_data['target']]['name']}**\n\nต้องการให้แนบปุ่มคลิกลิงก์ไปด้วยหรือไม่?", reply_markup=InlineKeyboardMarkup(kb))
    
    elif data.startswith("mode_"):
        context.user_data['mode'] = data.replace("mode_", "")
        mode_text = "มีปุ่มลิงก์" if context.user_data['mode'] == "with_kb" else "เฉพาะเนื้อหาเท่านั้น"
        await query.edit_message_text(f"ตั้งค่าเรียบร้อย! ✅\nกลุ่ม: **{ROUTES[context.user_data['target']]['name']}**\nโหมด: **{mode_text}**\n\n📌 **ส่งรูปหรือข้อความมาได้เลยครับ**")

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS or 'target' not in context.user_data: return
    
    route = ROUTES[context.user_data['target']]
    mode = context.user_data.get('mode', 'with_kb')
    kb = None
    caption = update.effective_message.caption or ""

    if mode == "with_kb":
        if route["type"] == "free":
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 ติดต่อแอดมิน", url=LINE_FREE_ADMIN)]])
            caption += "\n\nสนใจรับชมติดต่อแอดมินครับ 👇"
        else:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=LOGIN_URL)],
                [InlineKeyboardButton("📞 แอดมิน", url=LINE_PREMIUM_ADMIN), InlineKeyboardButton("💰 ฝาก-ถอน", url=LINE_DEPOSIT_WITHDRAW)],
                [InlineKeyboardButton("🔐 เข้าสู่ระบบ", url=LOGIN_URL)]
            ])

    try:
        if update.effective_message.photo:
            await context.bot.send_photo(chat_id=route["group_id"], photo=update.effective_message.photo[-1].file_id, caption=caption, parse_mode="HTML", reply_markup=kb, message_thread_id=route["thread_id"])
        else:
            await context.bot.send_message(chat_id=route["group_id"], text=update.effective_message.text, reply_markup=kb, message_thread_id=route["thread_id"], parse_mode="HTML")
        
        await update.message.reply_text("✅ ส่งเรียบร้อย!")
        context.user_data.clear() # ล้างค่าเพื่อรอส่งครั้งใหม่
    except Exception as e:
        await update.message.reply_text(f"❌ ผิดพลาด: {e}")

# --- ส่วน Live Stream (คงไว้ตามเดิม) ---
# ... (handle_live_started, handle_live_ended เหมือนโค้ดล่าสุด)

async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_admin))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler((filters.PHOTO | filters.TEXT) & (~filters.COMMAND), handle_broadcast))
    # handlers สำหรับสตรีม
    # application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started))
    # application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended))

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
