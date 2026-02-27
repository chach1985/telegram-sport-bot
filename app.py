from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


@app.route("/")
def home():
    return "Bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    print(json.dumps(data, indent=2), flush=True)

    if "channel_post" in data:
        message = data["channel_post"]["text"]
        source_chat_id = data["channel_post"]["chat"]["id"]

        target_group_id = os.environ.get("TARGET_GROUP_ID")
        topic_id = int(os.environ.get("TOPIC_ID", 0))

        payload = {
            "chat_id": target_group_id,
            "text": message,
        }

        if topic_id:
            payload["message_thread_id"] = topic_id

        requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
