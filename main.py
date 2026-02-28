import os
import asyncio
import signal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- ข้อมูลเดิมของคุณ ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
WEB_URL = "https://telegram-sport-bot-hk6a.onrender.com"

CHANNEL_ROUTES = {
    -1003742462075: [{"group_id": -1003749819628, "thread_id": 3}, {"group_id": -1003787225016, "thread_id": 2}],
    -1003735613798: [{"group_id": -1003749819628, "thread_id": 3}, {"group_id": -1003787225016, "thread_id": 2}],
}
ACTIVE_LIVES = {}

# --- Handlers เดิมของคุณ ---
async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if update.effective_chat.id in CHANNEL_ROUTES and message.video_chat_started:
        ACTIVE_LIVES[update.effective_chat.id] = message.message_id

async def handle_live_ended(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id in ACTIVE_LIVES and update.effective_message.video_chat_ended:
        ACTIVE_LIVES.pop(update.effective_chat.id, None)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in CHANNEL_ROUTES or chat_id not in ACTIVE_LIVES:
        return
    
    live_link = f"https://t.me/{update.effective_chat.username}/{ACTIVE_LIVES[chat_id]}"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎥 ดูสตรีมสด", url=live_link)]])
    
    for route in CHANNEL_ROUTES[chat_id]:
        await context.bot.send_photo(
            chat_id=route["group_id"],
            photo=update.effective_message.photo[-1].file_id,
            caption=update.effective_message.caption or "",
            reply_markup=keyboard,
            message_thread_id=route["thread_id"],
        )

# --- ส่วนการรันแบบใหม่เพื่อแก้ RuntimeError ---

async def run_bot():
    # 1. สร้าง Application
    application = Application.builder().token(TOKEN).build()

    # 2. เพิ่ม Handlers
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started))
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # 3. เริ่มต้น Webhook แบบ Manual เพื่อเลี่ยงปัญหา Event Loop
    await application.initialize()
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEB_URL}/{TOKEN}"
    )

    print(f"Bot is running on port {PORT}...")

    # สร้าง Event สำหรับรอปิดโปรแกรม (Keep-alive)
    stop_event = asyncio.Event()
    
    # จัดการการปิดโปรแกรมอย่างนุ่มนวล (SIGTERM/SIGINT)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    # รันค้างไว้จนกว่าจะมีการปิดโปรแกรม
    await stop_event.wait()

    # 4. ปิดระบบเมื่อจบการทำงาน
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    try:
        # ใช้ asyncio.run() ซึ่งเป็นมาตรฐานของ Python รุ่นใหม่ในการเริ่ม Loop
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
