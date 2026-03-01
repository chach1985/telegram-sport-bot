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

# --- ข้อมูลพื้นฐาน ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
WEB_URL = "https://telegram-sport-bot-hk6a.onrender.com"

# แยก ID กลุ่มตามที่คุณระบุ
GROUP_U_TV = -1003749819628          # กลุ่ม 1
GROUP_U_TV_PREMIUM = -1003787225016  # กลุ่ม 2

CHANNEL_ROUTES = {
    -1003742462075: [
        {"group_id": GROUP_U_TV, "thread_id": 3, "type": "free"},
        {"group_id": GROUP_U_TV_PREMIUM, "thread_id": 2, "type": "premium"}
    ],
    -1003735613798: [
        {"group_id": GROUP_U_TV, "thread_id": 3, "type": "free"},
        {"group_id": GROUP_U_TV_PREMIUM, "thread_id": 2, "type": "premium"}
    ],
}
ACTIVE_LIVES = {}

async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if update.effective_chat.id in CHANNEL_ROUTES and message.video_chat_started:
        ACTIVE_LIVES[update.effective_chat.id] = message.message_id
        print(f"Live started in {update.effective_chat.id}")

async def handle_live_ended(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id in ACTIVE_LIVES and update.effective_message.video_chat_ended:
        ACTIVE_LIVES.pop(update.effective_chat.id, None)
        print(f"Live ended in {update.effective_chat.id}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in CHANNEL_ROUTES or chat_id not in ACTIVE_LIVES:
        return
    
    # ดึงข้อมูล Message ID ของไลฟ์มาสร้างลิงก์
    live_message_id = ACTIVE_LIVES[chat_id]
    username = update.effective_chat.username
    if username:
        live_link = f"https://t.me/{username}/{live_message_id}"
    else:
        # กรณีช่องเป็น Private
        live_link = f"https://t.me/c/{str(chat_id)[4:]}/{live_message_id}"

    # ข้อความเชิญชวน (รองรับ HTML สำหรับการทำลิงก์ "คลิกที่นี่")
    ad_caption = (
        "🔴 <b>ถ่ายทอดสดเริ่มแล้ว!</b>\n"
        "อย่าพลาดความสนุก เชียร์สดไปพร้อมกันได้เลย\n\n"
        "สนใจรับชมหรือสอบถามเพิ่มเติม ติดต่อแอดมินได้ที่:\n"
        "🆔 Line: <a href='https://lin.ee/aw2rc3s'>คลิกที่นี่</a>"
    )

    # วนลูปส่งตามกลุ่มที่ตั้งค่าไว้
    for route in CHANNEL_ROUTES[chat_id]:
        try:
            if route["type"] == "free":
                # กลุ่ม 1: ส่งรูป + ข้อความเชิญชวน (ไม่มีปุ่ม)
                await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=update.effective_message.photo[-1].file_id,
                    caption=ad_caption,
                    parse_mode="HTML",
                    message_thread_id=route["thread_id"],
                )
            
            elif route["type"] == "premium":
                # กลุ่ม 2: ส่งรูป + ข้อความเชิญชวน + ปุ่มลิงก์สตรีม
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=live_link)]])
                await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=update.effective_message.photo[-1].file_id,
                    caption=ad_caption,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    message_thread_id=route["thread_id"],
                )
        except Exception as e:
            print(f"Error sending to {route['group_id']}: {e}")

# --- ระบบรันบอท (เหมือนเดิม) ---
async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started))
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    await application.initialize()
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEB_URL}/{TOKEN}"
    )
    print(f"Bot is running on port {PORT}...")
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
        print("Bot stopped.")

