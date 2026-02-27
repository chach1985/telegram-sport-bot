from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
GROUP_ID = -1003749819628

CHANNEL_CONFIG = {
    -1003742462075: {
        "topic_id": 3,
        "emoji": "⚽"
    },
    -1003735613798: {
        "topic_id": 2,
        "emoji": "🥊"
    }
}

def send_photo(topic_id, photo_file_id, caption, button_url):
    url = f"{API_URL}/sendPhoto"
    data = {
        "chat_id": GROUP_ID,
        "message_thread_id": topic_id,
        "photo": photo_file_id,
        "caption": caption,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "รับชมทันที",
                        "url": button_url
                    }
                ]
            ]
        }
    }
    requests.post(url, json=data)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.json

    if "message" not in update:
        return "ok"

    msg = update["message"]

    if "forward_from_chat" not in msg:
        return "ok"

    channel_id = msg["forward_from_chat"]["id"]

    if channel_id not in CHANNEL_CONFIG:
        return "ok"

    config = CHANNEL_CONFIG[channel_id]
    topic_id = config["topic_id"]
    emoji = config["emoji"]

    caption_text = msg.get("caption", "")
    lines = caption_text.split("\n")

    if len(lines) < 2:
        return "ok"

    match_name = lines[0].strip()
    match_time = lines[1].strip()

    new_caption = f"{emoji} {match_name}\n🕒 {match_time}"

    username = msg["forward_from_chat"].get("username")
    message_id = msg.get("forward_from_message_id")

    if username and message_id:
        post_link = f"https://t.me/{username}/{message_id}"
    else:
        post_link = "https://t.me"

    if "photo" in msg:
        photo = msg["photo"][-1]["file_id"]
        send_photo(topic_id, photo, new_caption, post_link)

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)