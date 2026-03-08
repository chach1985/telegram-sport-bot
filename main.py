import os
import asyncio
import signal
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
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
# CONFIG
# =====================================================

TOKEN   = os.environ.get("BOT_TOKEN")
PORT    = int(os.environ.get("PORT", 10000))
WEB_URL = os.environ.get("WEB_URL", "https://telegram-sport-bot-hk6a.onrender.com")
DATA_FILE = os.environ.get("DATA_PATH", "/etc/data/bot_data.json")

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing")

# Super Admin — แก้ไขได้เฉพาะในโค้ด ไม่มีใครลบได้
SUPER_ADMINS: list[int] = [7029914099, 5915826734]

# =====================================================
# LINKS (ชุดปุ่มตายตัวตามประเภทกลุ่ม)
# =====================================================

LINE_FREE_ADMIN       = "https://lin.ee/aw2rc3s"
LINE_PREMIUM_ADMIN    = "https://tinyurl.com/ufa345-24"
LINE_DEPOSIT_WITHDRAW = "https://lin.ee/oi2hRtr"
LOGIN_URL             = "https://member.ufa345word.com/login"

# =====================================================
# GROUPS & TOPICS
# =====================================================

CLUB_UFA_TV    = -1003749819628
CLUB_BALLZA_TV = -1003787225016
CLUB_PAKYOK_TV = -1003709427421

# broadcast targets ที่ admin เลือกได้
# key = callback_data identifier
BROADCAST_TARGETS: dict[str, dict] = {
    "ufa_football": {
        "label":     "⚽ CLUB UFA TV — ฟุตบอล",
        "group_id":  CLUB_UFA_TV,
        "thread_id": 129,
        "type":      "free",
    },
    "ufa_muay": {
        "label":     "🥊 CLUB UFA TV — มวย",
        "group_id":  CLUB_UFA_TV,
        "thread_id": 133,
        "type":      "free",
    },
    "ballza": {
        "label":     "💎 CLUB BALLZA",
        "group_id":  CLUB_BALLZA_TV,
        "thread_id": 1,
        "type":      "premium",
    },
    "pakyok": {
        "label":     "💎 CLUB PAKYOK TV",
        "group_id":  CLUB_PAKYOK_TV,
        "thread_id": 1,
        "type":      "premium",
    },
}

# =====================================================
# STREAM ROUTES (Channel → Groups auto-forward)
# =====================================================

CHANNEL_ROUTES: dict[int, list[dict]] = {
    # ---- CLUB BALLZA channels ----
    -1003742462075: [  # สเตเดี้ยม 1
        {"group_id": CLUB_UFA_TV,    "thread_id": 3, "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"},
    ],
    -1003735613798: [  # สเตเดี้ยม 2
        {"group_id": CLUB_UFA_TV,    "thread_id": 3, "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"},
    ],
    -1003502971775: [  # สเตเดี้ยม 3
        {"group_id": CLUB_UFA_TV,    "thread_id": 3, "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"},
    ],
    -1003898955742: [  # สเตเดี้ยม 4
        {"group_id": CLUB_UFA_TV,    "thread_id": 3, "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"},
    ],
    -1003427683772: [  # สเตเดี้ยม 5
        {"group_id": CLUB_UFA_TV,    "thread_id": 3, "type": "free"},
        {"group_id": CLUB_BALLZA_TV, "thread_id": 2, "type": "premium"},
    ],
    # ---- CLUB PAKYOK channel ----
    -1003866345716: [  # สนามมวย
        {"group_id": CLUB_UFA_TV,    "thread_id": 3, "type": "free"},
        {"group_id": CLUB_PAKYOK_TV, "thread_id": 2, "type": "premium"},
    ],
}

# =====================================================
# DATABASE
# =====================================================

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"load_data failed: {e} — using empty state")
    return {"active_lives": {}, "sent_messages": {}, "admins": []}


def save_data() -> None:
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump({
                "active_lives":  ACTIVE_LIVES,
                "sent_messages": SENT_MESSAGES,
                "admins":        ADMIN_IDS,
            }, f, indent=2)
    except Exception as e:
        logger.error(f"save_data failed: {e}")


_data        = load_data()
ACTIVE_LIVES:  dict       = _data.get("active_lives", {})
SENT_MESSAGES: dict       = _data.get("sent_messages", {})
ADMIN_IDS:     list[int]  = [int(x) for x in _data.get("admins", [])]

_state_lock = asyncio.Lock()

# =====================================================
# AUTH HELPERS
# =====================================================

def is_super_admin(user_id: int) -> bool:
    return user_id in SUPER_ADMINS

def is_admin(user_id: int) -> bool:
    return user_id in SUPER_ADMINS or user_id in ADMIN_IDS

# =====================================================
# KEYBOARD HELPERS
# =====================================================

def kb_free_buttons() -> InlineKeyboardMarkup:
    """ปุ่มสำหรับกลุ่มฟรี"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 ติดต่อแอดมินเพื่อรับชม", url=LINE_FREE_ADMIN)]
    ])

def kb_premium_buttons(live_link: str | None = None) -> InlineKeyboardMarkup:
    """ปุ่มสำหรับกลุ่ม Premium (broadcast ไม่มี live_link)"""
    rows = []
    if live_link:
        rows.append([InlineKeyboardButton("🎥 เข้าชมถ่ายทอดสด", url=live_link)])
    rows.append([
        InlineKeyboardButton("📞 ติดต่อแอดมิน",      url=LINE_PREMIUM_ADMIN),
        InlineKeyboardButton("💰 ฝาก-ถอน",            url=LINE_DEPOSIT_WITHDRAW),
    ])
    rows.append([InlineKeyboardButton("🔐 เข้าสู่ระบบเว็บไซต์", url=LOGIN_URL)])
    return InlineKeyboardMarkup(rows)

def build_live_link(chat_id: str, live_message_id: int, username: str | None) -> str:
    if username:
        return f"https://t.me/{username}/{live_message_id}"
    try:
        peer_id = str(abs(int(chat_id)) - 1_000_000_000_000)
    except ValueError:
        peer_id = chat_id.lstrip("-100")
    return f"https://t.me/c/{peer_id}/{live_message_id}"

# =====================================================
# STREAM HANDLERS
# =====================================================

async def handle_live_started(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat_id = str(update.effective_chat.id)

    if int(chat_id) not in CHANNEL_ROUTES or not message.video_chat_started:
        return

    async with _state_lock:
        ACTIVE_LIVES[chat_id]  = message.message_id
        SENT_MESSAGES[chat_id] = []
        save_data()

    logger.info(f"[LIVE STARTED] channel={chat_id}")


async def handle_live_ended(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                    logger.warning(f"[DELETE] msg={msg_info['message_id']} error={e}")

        SENT_MESSAGES.pop(chat_id, None)
        ACTIVE_LIVES.pop(chat_id, None)
        save_data()

    logger.info(f"[LIVE ENDED] channel={chat_id} premium_deleted={deleted}")


async def handle_photo_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """รับรูปจาก Channel → ส่งต่อไปทุก route อัตโนมัติ"""
    if update.effective_chat.type != "channel":
        return

    chat_id = str(update.effective_chat.id)

    if int(chat_id) not in CHANNEL_ROUTES or chat_id not in ACTIVE_LIVES:
        return

    live_message_id = ACTIVE_LIVES[chat_id]
    live_link       = build_live_link(chat_id, live_message_id, update.effective_chat.username)
    photo_file_id   = update.effective_message.photo[-1].file_id
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
                    reply_markup=kb_free_buttons(),
                    message_thread_id=route["thread_id"],
                )
            else:
                sent = await context.bot.send_photo(
                    chat_id=route["group_id"],
                    photo=photo_file_id,
                    caption="",
                    reply_markup=kb_premium_buttons(live_link),
                    message_thread_id=route["thread_id"],
                )

            new_sent.append({
                "group_id":   route["group_id"],
                "message_id": sent.message_id,
                "type":       route["type"],
            })
            logger.info(f"[STREAM] channel={chat_id} → group={route['group_id']} type={route['type']}")

        except Exception as e:
            logger.error(f"[STREAM ERROR] channel={chat_id} group={route['group_id']} error={e}")

    async with _state_lock:
        SENT_MESSAGES.setdefault(chat_id, []).extend(new_sent)
        save_data()

# =====================================================
# BROADCAST — Step 1: /broadcast → เลือกกลุ่ม
# =====================================================

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """เริ่ม flow broadcast — เฉพาะ Admin เท่านั้น"""
    if update.effective_chat.type != "private":
        return
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return

    context.user_data.clear()

    rows = []
    for key, t in BROADCAST_TARGETS.items():
        rows.append([InlineKeyboardButton(
            f"☐ {t['label']}",
            callback_data=f"bc_sel_{key}"
        )])
    rows.append([InlineKeyboardButton("✅ ยืนยันกลุ่มที่เลือก →", callback_data="bc_confirm_targets")])

    await update.message.reply_text(
        "📢 <b>Broadcast — เลือกกลุ่มเป้าหมาย</b>\n"
        "กดเลือกได้หลายกลุ่ม แล้วกด ✅ ยืนยัน",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(rows),
    )


def _render_target_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """สร้างปุ่มเลือกกลุ่ม พร้อม ☑/☐ ตามสถานะ"""
    rows = []
    for key, t in BROADCAST_TARGETS.items():
        mark = "☑" if key in selected else "☐"
        rows.append([InlineKeyboardButton(
            f"{mark} {t['label']}",
            callback_data=f"bc_sel_{key}"
        )])
    rows.append([InlineKeyboardButton("✅ ยืนยันกลุ่มที่เลือก →", callback_data="bc_confirm_targets")])
    return InlineKeyboardMarkup(rows)

# =====================================================
# BROADCAST — Step 2: เลือกใส่ปุ่มหรือไม่
# =====================================================

def _render_button_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ใส่ปุ่มลิงก์",  callback_data="bc_btn_yes"),
            InlineKeyboardButton("❌ ไม่ใส่ปุ่ม",    callback_data="bc_btn_no"),
        ]
    ])

# =====================================================
# BROADCAST — Callback handler (Step 1 + 2)
# =====================================================

async def bc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if not is_admin(query.from_user.id):
        await query.answer("⛔ ไม่มีสิทธิ์", show_alert=True)
        return

    await query.answer()
    data = query.data

    # --- toggle เลือก/ยกเลิกกลุ่ม ---
    if data.startswith("bc_sel_"):
        key      = data[len("bc_sel_"):]
        selected: set = context.user_data.setdefault("bc_selected", set())

        if key in selected:
            selected.discard(key)
        else:
            selected.add(key)

        await query.edit_message_reply_markup(
            reply_markup=_render_target_keyboard(selected)
        )
        return

    # --- ยืนยันกลุ่ม → ถามเรื่องปุ่ม ---
    if data == "bc_confirm_targets":
        selected = context.user_data.get("bc_selected", set())
        if not selected:
            await query.answer("⚠️ กรุณาเลือกกลุ่มอย่างน้อย 1 กลุ่ม", show_alert=True)
            return

        labels = "\n".join(f"• {BROADCAST_TARGETS[k]['label']}" for k in selected)
        await query.edit_message_text(
            f"📋 <b>กลุ่มที่เลือก:</b>\n{labels}\n\n"
            f"🔘 ต้องการแนบปุ่มลิงก์ใต้ข้อความไหม?\n"
            f"<i>(ฟรี = ปุ่มติดต่อแอดมิน / Premium = ปุ่มแอดมิน+ฝากถอน+Login)</i>",
            parse_mode="HTML",
            reply_markup=_render_button_keyboard(),
        )
        return

    # --- เลือกใส่/ไม่ใส่ปุ่ม → รอรับเนื้อหา ---
    if data in ("bc_btn_yes", "bc_btn_no"):
        context.user_data["bc_with_buttons"] = (data == "bc_btn_yes")
        btn_status = "✅ มีปุ่มลิงก์" if data == "bc_btn_yes" else "❌ ไม่มีปุ่ม"

        selected = context.user_data.get("bc_selected", set())
        labels   = "\n".join(f"• {BROADCAST_TARGETS[k]['label']}" for k in selected)

        context.user_data["bc_ready"] = True

        await query.edit_message_text(
            f"✅ <b>พร้อมส่งแล้ว!</b>\n\n"
            f"📋 <b>กลุ่ม:</b>\n{labels}\n\n"
            f"🔘 <b>ปุ่มลิงก์:</b> {btn_status}\n\n"
            f"📩 <b>ส่งรูป หรือ พิมพ์ข้อความมาได้เลยครับ</b>",
            parse_mode="HTML",
        )
        return

# =====================================================
# BROADCAST — Step 3: รับเนื้อหาและส่ง
# =====================================================

async def handle_bc_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """รับรูปหรือข้อความจาก Admin แล้วส่งไปยังกลุ่มที่เลือก"""
    if update.effective_chat.type != "private":
        return
    if not is_admin(update.effective_user.id):
        return
    if not context.user_data.get("bc_ready"):
        return

    selected     = context.user_data.get("bc_selected", set())
    with_buttons = context.user_data.get("bc_with_buttons", False)
    msg          = update.effective_message

    if not selected:
        await msg.reply_text("⚠️ ไม่พบกลุ่มเป้าหมาย กรุณาเริ่มใหม่ด้วย /broadcast")
        return

    success, failed = 0, 0

    for key in selected:
        target = BROADCAST_TARGETS[key]
        keyboard = None

        if with_buttons:
            if target["type"] == "free":
                keyboard = kb_free_buttons()
            else:
                keyboard = kb_premium_buttons()   # broadcast ไม่มี live_link

        try:
            if msg.photo:
                await context.bot.send_photo(
                    chat_id=target["group_id"],
                    photo=msg.photo[-1].file_id,
                    caption=msg.caption or "",
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    message_thread_id=target["thread_id"],
                )
            elif msg.text:
                await context.bot.send_message(
                    chat_id=target["group_id"],
                    text=msg.text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    message_thread_id=target["thread_id"],
                )
            else:
                await msg.reply_text("⚠️ รองรับเฉพาะรูปภาพและข้อความเท่านั้น")
                return

            success += 1
            logger.info(f"[BROADCAST] → {target['label']} by user={update.effective_user.id}")

        except Exception as e:
            failed += 1
            logger.error(f"[BROADCAST ERROR] target={key} error={e}")

    result = f"📤 ส่งเรียบร้อย {success} กลุ่ม"
    if failed:
        result += f" | ❌ ส่งไม่สำเร็จ {failed} กลุ่ม"

    await msg.reply_text(result)
    context.user_data.clear()

# =====================================================
# ADMIN MANAGEMENT (Super Admin only)
# =====================================================

async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return
    if not is_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ เฉพาะ Super Admin เท่านั้น")
        return

    if not context.args:
        await update.message.reply_text("📌 วิธีใช้: /addadmin <user_id>")
        return

    try:
        new_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ user_id ต้องเป็นตัวเลข")
        return

    if new_id in SUPER_ADMINS:
        await update.message.reply_text("ℹ️ ID นี้เป็น Super Admin อยู่แล้ว")
        return

    if new_id not in ADMIN_IDS:
        ADMIN_IDS.append(new_id)
        save_data()
        await update.message.reply_text(f"✅ เพิ่ม Admin {new_id} แล้ว")
    else:
        await update.message.reply_text("ℹ️ ID นี้เป็น Admin อยู่แล้ว")


async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return
    if not is_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ เฉพาะ Super Admin เท่านั้น")
        return

    if not context.args:
        await update.message.reply_text("📌 วิธีใช้: /removeadmin <user_id>")
        return

    try:
        rem_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ user_id ต้องเป็นตัวเลข")
        return

    if rem_id in SUPER_ADMINS:
        await update.message.reply_text("⛔ ไม่สามารถลบ Super Admin ได้")
        return

    if rem_id in ADMIN_IDS:
        ADMIN_IDS.remove(rem_id)
        save_data()
        await update.message.reply_text(f"✅ ลบ Admin {rem_id} แล้ว")
    else:
        await update.message.reply_text("⚠️ ไม่พบ ID นี้ในรายการ Admin")


async def cmd_listadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return
    if not is_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ เฉพาะ Super Admin เท่านั้น")
        return

    super_list = "\n".join(f"  ⭐ {uid}" for uid in SUPER_ADMINS)
    admin_list = "\n".join(f"  👤 {uid}" for uid in ADMIN_IDS) if ADMIN_IDS else "  (ไม่มี)"

    await update.message.reply_text(
        f"📋 <b>รายชื่อ Admin</b>\n\n"
        f"<b>Super Admin:</b>\n{super_list}\n\n"
        f"<b>Admin:</b>\n{admin_list}",
        parse_mode="HTML",
    )

# =====================================================
# /start — แสดงคำสั่งที่ใช้ได้
# =====================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return

    uid = update.effective_user.id

    if is_super_admin(uid):
        role = "⭐ Super Admin"
        cmds = (
            "/broadcast — ส่งข้อความ/รูปไปยังกลุ่ม\n"
            "/addadmin &lt;id&gt; — เพิ่ม Admin\n"
            "/removeadmin &lt;id&gt; — ลบ Admin\n"
            "/listadmin — ดูรายชื่อ Admin"
        )
    elif is_admin(uid):
        role = "👤 Admin"
        cmds = "/broadcast — ส่งข้อความ/รูปไปยังกลุ่ม"
    else:
        await update.message.reply_text("⛔ คุณไม่มีสิทธิ์ใช้งาน bot นี้")
        return

    await update.message.reply_text(
        f"👋 สวัสดี! สถานะของคุณ: <b>{role}</b>\n\n"
        f"📌 <b>คำสั่งที่ใช้ได้:</b>\n{cmds}",
        parse_mode="HTML",
    )

# =====================================================
# BOT STARTUP
# =====================================================

async def run_bot() -> None:
    application = Application.builder().token(TOKEN).build()

    # Stream handlers
    application.add_handler(MessageHandler(
        filters.StatusUpdate.VIDEO_CHAT_STARTED, handle_live_started
    ))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.VIDEO_CHAT_ENDED, handle_live_ended
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.CHANNEL & filters.PHOTO, handle_photo_stream
    ))

    # Admin management
    application.add_handler(CommandHandler("start",       cmd_start))
    application.add_handler(CommandHandler("addadmin",    cmd_addadmin))
    application.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    application.add_handler(CommandHandler("listadmin",   cmd_listadmin))

    # Broadcast flow
    application.add_handler(CommandHandler("broadcast", cmd_broadcast))
    application.add_handler(CallbackQueryHandler(bc_callback, pattern=r"^bc_"))
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.PHOTO | filters.TEXT) & ~filters.COMMAND,
        handle_bc_content
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
