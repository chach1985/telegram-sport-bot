import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# ดึงค่าจาก Environment Variables
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
# URL ของคุณจาก Render
WEB_URL = "https://telegram-sport-bot-hk6a.onrender.com"

CHANNEL_ROUTES = {
    -1003742462075: [
        {"group_id": -1003749819628, "thread_id": 3},
        {"group_id": -1003787225016, "thread_id": 2},
    ],
    -1003735613798: [
        {"group_id": -1003749819628, "thread_id": 3},
        {"group_id": -1003787225016, "thread_id": 2},
    ],
}

ACTIVE_LIVES = {}

async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = update.effective_chat.id
    if chat_id in CHANNEL_ROUTES and message.video_chat_started:
        ACTIVE_LIVES[chat_id] = message.message_id
        print(f"Live started in {chat_id}")

async def handle_live_ended(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = update.effective_chat.id
    if chat_id in ACTIVE_LIVES and message.video_chat_ended:
        ACTIVE_LIVES.pop(chat_id, None)
        print(f"Live ended in {chat_id}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = update.effective_chat.id

    if chat_id not in CHANNEL_ROUTES or chat_id not in ACTIVE_LIVES:
        return

    live_message_id = ACTIVE_LIVES[chat_id]
    username = update.effective_chat.username
    live_link = f"https://t.me/{username}/{live_message_id}" if username else f"https://t.me/c/{str(chat_id)[4:]}/{live_message_id}"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎥 ดูสตรีมสด", url=live_link)]])
    photo_file_id = message.photo[-1].file_id
    caption = message.caption or ""

    for route in CHANNEL_ROUTES[chat_id]:
        await context.bot.send_photo(
            chat_id=route["group_id"],
            photo=photo_file_id,
            caption=caption,
            reply_markup=keyboard,
            message_thread_id=route["thread_id"],
        )

def main():
    """ฟังก์ชันหลักสำหรับรันบอท"""
    application = Application.builder().token(TOKEN).build()

    # เพิ่ม Handlers
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started))
    application.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # รัน Webhook (ตัวนี้จะจัดการ Event Loop และ Web Server ให้เอง)
    print(f"Starting bot on port {PORT}...")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEB_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
