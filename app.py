import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ====== CONFIG ======
CHANNEL_A_ID = -1003749819628
CHANNEL_B_ID = -1003735613798

GROUP_ID = -1003749819628
[LIVE] สเตเดี้ยม 1_ID = 3
[LIVE] สเตเดี้ยม 2_ID = 2
# ====================


@app.route("/")
def home():
    return "STREAM ROUTER ACTIVE"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "channel_post" in data:
        post = data["channel_post"]
        source_chat_id = post["chat"]["id"]

        text = post.get("text", "")
        caption = post.get("caption", "")

        if source_chat_id == CHANNEL_A_ID:
            send_to_topic(post, TOPIC_A_ID, "https://t.me/YourChannelAUsername")

        elif source_chat_id == CHANNEL_B_ID:
            send_to_topic(post, TOPIC_B_ID, "https://t.me/YourChannelBUsername")

    return jsonify({"status": "ok"})


def send_to_topic(post, topic_id, channel_link):

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🔴 ดูสดที่ต้นทาง",
                    "url": channel_link
                }
            ]
        ]
    }

    # ถ้ามีรูป
    if "photo" in post:
        photo = post["photo"][-1]["file_id"]
        caption = post.get("caption", "")

        requests.post(f"{API_URL}/sendPhoto", json={
            "chat_id": GROUP_ID,
            "message_thread_id": topic_id,
            "photo": photo,
            "caption": caption,
            "reply_markup": keyboard
        })

    # ถ้าเป็นข้อความล้วน
    elif "text" in post:
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": GROUP_ID,
            "message_thread_id": topic_id,
            "text": post["text"],
            "reply_markup": keyboard
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
