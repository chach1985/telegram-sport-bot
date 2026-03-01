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

# ลิงก์ Line@ ของคุณ
LINE_ADMIN_URL = "https://lin.ee/aw2rc3s"

GROUP_U_TV = -1003749819628          
GROUP_U_TV_PREMIUM = -1003787225016  

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
SENT_MESSAGES = {} 

async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = update.effective_chat.id
    if chat_id in CHANNEL_ROUTES and message.video_chat_started:
        ACTIVE_LIVES[chat_id] = message.message_id
        SENT_MESSAGES[chat_id] = [] 
        print(f"Live started in {chat_id}")

async def handle_live_ended(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in ACTIVE_LIVES and update.effective_message.video_chat_ended:
        if chat_id in SENT_MESSAGES:
            for msg_info in SENT_MESSAGES[chat_id]:
                try:
                    await context.bot.delete_message(
                        chat_id=msg_info["group_id"],
                        message_id=msg_info["message_id"]
                    )
                except Exception as e:
                    print(f"Delete error: {e}")
            SENT_MESSAGES.pop(chat_id, None)
        
        ACTIVE_LIVES.pop(chat_id, None)
        print(f"Live ended and messages cleaned in {chat_id}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in CHANNEL_ROUTES or chat_id not in ACTIVE_LIVES:
        return
    
    live_message_id = ACTIVE_LIVES[chat_id]
    username = update.effective_chat.username
    live_link = f"https://t.me/{username}/{live_message_id}" if username else f"https://t.me/c/{str(chat_id)[4:]}/{live_message_id}"

    # ข้อความเชียร์สดสำหรับกลุ่มฟรี (นำลิงก์ออกจากข้อความแล้วไปใส่ที่ปุ่มแทน)
    ad_caption = (
        "🔴 <b>ถ่ายทอดสดเริ่มแล้ว!</b>\n"
        "อย่าพลาดความสนุก เชียร์สดไปพร้อมกันได้เลย\n\n"
        "สนใจรับชมหรือสอบถามเพิ่มเติม ติดต่อแอดมินได้ที่ปุ่มด้านล่าง 👇"
    )

    for route in CHANNEL_ROUTES[chat_id]:
        try:
            sent_msg = None
            if route["type"] == "free":
                # กลุ่มฟรี: ปุ่มติดต่อแอดมินในไลน์
                free_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 ติดต่อแอดมินเพื่อรับชม", url=LINE_ADMIN_URL)]
                ])
                sent_msg = await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=update.effective_message.photo[-1].file_id,
                    caption=ad_caption,
                    parse_mode="HTML",
                    reply_markup=free_keyboard,
                    message_thread_id=route["thread_id"],
                )
            elif route["type"] == "premium":
                # กลุ่ม Premium: ปุ่มเข้าดูสตรีมโดยตรง (ไม่มีข้อความ)
                premium_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=live_link)]
                ])
                sent_msg = await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=update.effective_message.photo[-1].file_id,
                    caption="",
                    reply_markup=premium_keyboard,
                    message_thread_id=route["thread_id"],
                )
            
            if sent_msg:
                SENT_MESSAGES[chat_id].append({
                    "group_id": route["group_id"],
                    "message_id": sent_msg.message_id
                })

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
