import os
import asyncio
import signal
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIG — ดึงจาก Environment Variables
# =====================================================

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
WEB_URL = os.environ.get("WEB_URL", "https://telegram-sport-bot-hk6a.onrender.com")
DATA_FILE = os.environ.get("DATA_PATH", "/etc/data/bot_data.json")

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing")

# =====================================================
# LINKS
# =====================================================

LINE_FREE_ADMIN      = "https://lin.ee/aw2rc3s"
LINE_PREMIUM_ADMIN   = "https://tinyurl.com/ufa345-24"
LINE_DEPOSIT_WITHDRAW = "https://lin.ee/oi2hRtr"
LOGIN_URL            = "https://member.ufa345word.com/login"

# =====================================================
# TARGET GROUPS
# =====================================================

CLUB_UFA_TV    = -1003749819628
CLUB_BALLZA_TV = -1003787225016
CLUB_PAKYOK_TV = -1003709427421

# =====================================================
# CHANNEL ROUTES
# format: { channel_id: [ free_route, premium_route ] }
#
# free route    → ประกาศ + ปุ่มติดต่อแอดมิน (ไม่ลบเมื่อจบ)
# premium route → ประกาศ + ปุ่มดูสด + ปุ่มอื่นๆ (ลบเมื่อจบ)
# =====================================================

CHANNEL_ROUTES = {
    -1003742462075: [
        {"group_id": CLUB_UFA_TV,    "thread_id": 3,  "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2,  "type": "premium"},
    ],
    -1003735613798: [
        {"group_id": CLUB_UFA_TV,    "thread_id": 3,  "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2,  "type": "premium"},
    ],
    -1003866345716: [
        {"group_id": CLUB_UFA_TV,    "thread_id": 3,  "type": "free"},
        {"group_id": CLUB_PAKYOK_TV, "thread_id": 2,  "type": "premium"},
    ],
    -1003502971775: [
        {"group_id": CLUB_UFA_TV,    "thread_id": 3,  "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2,  "type": "premium"},
    ],
    -1003898955742: [
        {"group_id": CLUB_UFA_TV,    "thread_id": 3,  "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2,  "type": "premium"},
    ],
    -1003427683772: [
        {"group_id": CLUB_UFA_TV,    "thread_id": 3,  "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2,  "type": "premium"},
    ],
}

# =====================================================
# DATABASE (JSON file)
# =====================================================

def load_data() -> dict:
    """โหลดข้อมูล active_lives และ sent_messages จากไฟล์"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"load_data failed: {e} — using empty state")
    return {"active_lives": {}, "sent_messages": {}}


def save_data() -> None:
    """บันทึก state ปัจจุบันลงไฟล์"""
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump({"active_lives": ACTIVE_LIVES, "sent_messages": SENT_MESSAGES}, f, indent=2)
    except Exception as e:
        logger.error(f"save_data failed: {e}")


_data = load_data()
ACTIVE_LIVES: dict  = _data.get("active_lives", {})   # { chat_id(str): live_message_id }
SENT_MESSAGES: dict = _data.get("sent_messages", {})   # { chat_id(str): [ {group_id, message_id, type} ] }

# Lock สำหรับป้องกัน race condition เมื่อหลาย channel live พร้อมกัน
_state_lock = asyncio.Lock()

# =====================================================
# HELPERS
# =====================================================

def build_live_link(chat_id: str, live_message_id: int, username: str | None) -> str:
    """สร้างลิงก์ไปยัง video chat"""
    if username:
        return f"https://t.me/{username}/{live_message_id}"
    # chat_id ของ supergroup/channel มีรูปแบบ -100XXXXXXXXXX
    # ตัด -100 ออกเพื่อใช้ใน t.me/c/
    try:
        peer_id = str(abs(int(chat_id)) - 1_000_000_000_000)
    except ValueError:
        peer_id = chat_id.lstrip("-100")
    return f"https://t.me/c/{peer_id}/{live_message_id}"


def build_free_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 ติดต่อแอดมินเพื่อรับชม", url=LINE_FREE_ADMIN)]
    ])


def build_premium_keyboard(live_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=live_link)],
        [
            InlineKeyboardButton("📞 ติดต่อแอดมิน",  url=LINE_PREMIUM_ADMIN),
            InlineKeyboardButton("💰 ฝาก-ถอน",       url=LINE_DEPOSIT_WITHDRAW),
        ],
        [InlineKeyboardButton("🔐 เข้าสู่ระบบเว็บไซต์", url=LOGIN_URL)],
    ])

# =====================================================
# HANDLERS
# =====================================================

async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """บันทึก message_id ของ video chat เมื่อ live เริ่ม"""
    message = update.effective_message
    chat_id = str(update.effective_chat.id)

    if int(chat_id) not in CHANNEL_ROUTES:
        return
    if not message.video_chat_started:
        return

    async with _state_lock:
        ACTIVE_LIVES[chat_id] = message.message_id
        SENT_MESSAGES[chat_id] = []
        save_data()

    logger.info(f"[LIVE STARTED] channel={chat_id} live_msg={message.message_id}")


async def handle_live_ended(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    เมื่อ live จบ:
    - ลบเฉพาะข้อความใน กลุ่ม Premium
    - คงข้อความใน กลุ่ม Free ไว้ (ตามดีไซน์)
    """
    chat_id = str(update.effective_chat.id)

    if not update.effective_message.video_chat_ended:
        return

    async with _state_lock:
        if chat_id not in ACTIVE_LIVES:
            return

        deleted = 0
        for msg_info in SENT_MESSAGES.get(chat_id, []):
            if msg_info.get("type") == "premium":
                try:
                    await context.bot.delete_message(
                        chat_id=msg_info["group_id"],
                        message_id=msg_info["message_id"],
                    )
                    deleted += 1
                except Exception as e:
                    logger.warning(f"[DELETE] failed msg={msg_info['message_id']} error={e}")

        SENT_MESSAGES.pop(chat_id, None)
        ACTIVE_LIVES.pop(chat_id, None)
        save_data()

    logger.info(f"[LIVE ENDED] channel={chat_id} premium_deleted={deleted}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    รับรูปจาก Channel → ส่งต่อไปยังกลุ่มเป้าหมายทุกกลุ่มตาม route
    เงื่อนไข: ต้องเป็น channel, อยู่ใน CHANNEL_ROUTES และมี live กำลังดำเนินอยู่
    """
    # กรองเฉพาะ channel เท่านั้น
    if update.effective_chat.type != "channel":
        return

    chat_id = str(update.effective_chat.id)

    if int(chat_id) not in CHANNEL_ROUTES:
        return
    if chat_id not in ACTIVE_LIVES:
        return

    live_message_id = ACTIVE_LIVES[chat_id]
    username = update.effective_chat.username
    live_link = build_live_link(chat_id, live_message_id, username)
    photo_file_id = update.effective_message.photo[-1].file_id

    new_sent: list[dict] = []

    for route in CHANNEL_ROUTES[int(chat_id)]:
        try:
            if route["type"] == "free":
                caption = (
                    "🔴 <b>ถ่ายทอดสดเริ่มแล้ว!</b>\n"
                    "อย่าพลาดความสนุก เชียร์สดไปพร้อมกันได้เลย\n\n"
                    "สนใจรับชมหรือสอบถามเพิ่มเติม ติดต่อแอดมินได้ที่ปุ่มด้านล่าง 👇"
                )
                sent = await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=photo_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=build_free_keyboard(),
                    message_thread_id=route["thread_id"],
                )

            else:  # premium
                sent = await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=photo_file_id,
                    caption="",
                    reply_markup=build_premium_keyboard(live_link),
                    message_thread_id=route["thread_id"],
                )

            new_sent.append({
                "group_id": route["group_id"],
                "message_id": sent.message_id,
                "type": route["type"],
            })
            logger.info(f"[SENT] channel={chat_id} → group={route['group_id']} type={route['type']}")

        except Exception as e:
            logger.error(f"[SEND ERROR] channel={chat_id} group={route['group_id']} error={e}")

    # อัปเดต state และบันทึกครั้งเดียวหลัง loop
    async with _state_lock:
        SENT_MESSAGES.setdefault(chat_id, []).extend(new_sent)
        save_data()

# =====================================================
# BOT STARTUP
# =====================================================

async def run_bot() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(MessageHandler(
        filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started
    ))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.CHANNEL & filters.PHOTO, handle_photo
    ))

    await application.initialize()
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEB_URL}/{TOKEN}",
    )

    logger.info(f"Bot started — webhook: {WEB_URL}/{TOKEN}")

    # รอจนกว่าจะได้รับ signal หยุด
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()

    logger.info("Shutting down...")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        pass
